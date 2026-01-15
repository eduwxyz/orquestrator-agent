"""Main orchestrator service for autonomous goal execution."""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from ..config.settings import get_settings
from ..models.orchestrator import GoalStatus, ActionType, OrchestratorLogType
from ..models.card import Card
from ..repositories.orchestrator_repository import GoalRepository, ActionRepository, LogRepository
from ..repositories.card_repository import CardRepository
from .memory_service import MemoryService
from .usage_checker_service import get_usage_checker_service, UsageInfo
from .orchestrator_logger import get_orchestrator_logger

logger = logging.getLogger(__name__)


class OrchestratorDecision(str, Enum):
    """Decisions the orchestrator can make."""
    VERIFY_LIMIT = "verify_limit"
    DECOMPOSE = "decompose"
    EXECUTE_CARD = "execute_card"
    CREATE_FIX = "create_fix"
    WAIT = "wait"
    COMPLETE_GOAL = "complete_goal"


@dataclass
class ThinkResult:
    """Result of the THINK step."""
    decision: OrchestratorDecision
    goal_id: Optional[str] = None
    card_id: Optional[str] = None
    reason: str = ""
    context: Optional[Dict[str, Any]] = None


@dataclass
class ActResult:
    """Result of the ACT step."""
    success: bool
    should_learn: bool = False
    learning: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class OrchestratorService:
    """
    Main orchestrator service that runs the autonomous loop.

    Loop steps:
    1. READ - Check short-term memory for recent context
    2. QUERY - Query long-term memory for relevant learnings
    3. THINK - Decide next action
    4. ACT - Execute the decision
    5. RECORD - Save result to short-term memory
    6. LEARN - If significant learning, save to Qdrant
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.goal_repo = GoalRepository(session)
        self.action_repo = ActionRepository(session)
        self.log_repo = LogRepository(session, self.settings.short_term_memory_retention_hours)
        self.card_repo = CardRepository(session)
        self.memory = MemoryService(session, self.settings.short_term_memory_retention_hours)
        self.usage_checker = get_usage_checker_service(self.settings.orchestrator_usage_limit_percent)
        self.logger = get_orchestrator_logger(self.settings.orchestrator_log_file)

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_usage_check: Optional[UsageInfo] = None

    # ==================== LOOP CONTROL ====================

    async def start(self) -> None:
        """Start the orchestrator loop."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        await self.logger.log_info("Orchestrator started")
        logger.info("[Orchestrator] Started")

    async def stop(self) -> None:
        """Stop the orchestrator loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.logger.log_info("Orchestrator stopped")
        logger.info("[Orchestrator] Stopped")

    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self._running

    async def _run_loop(self) -> None:
        """Main orchestrator loop."""
        while self._running:
            try:
                await self._execute_cycle()
            except Exception as e:
                logger.exception(f"[Orchestrator] Error in loop: {e}")
                await self.logger.log_error(f"Loop error: {e}")

            # Wait for next cycle
            await asyncio.sleep(self.settings.orchestrator_loop_interval_seconds)

    # ==================== MAIN CYCLE ====================

    async def _execute_cycle(self) -> None:
        """Execute one cycle of the orchestrator loop."""
        cycle_start = datetime.utcnow()
        await self.logger.log_info(f"Starting cycle at {cycle_start.isoformat()}")

        # Step 1: READ - Get recent context
        await self.logger.log_read("Reading short-term memory...")
        context = await self._step_read()

        # Step 2: QUERY - Get relevant learnings
        await self.logger.log_query("Querying long-term memory...")
        learnings = await self._step_query(context)

        # Step 3: THINK - Decide action
        await self.logger.log_think("Deciding next action...")
        think_result = await self._step_think(context, learnings)
        await self.logger.log_think(
            f"Decision: {think_result.decision.value} - {think_result.reason}",
            goal_id=think_result.goal_id
        )

        # Step 4: ACT - Execute decision
        await self.logger.log_act(f"Executing {think_result.decision.value}...")
        act_result = await self._step_act(think_result)

        # Step 5: RECORD - Save to short-term memory
        await self.logger.log_record("Recording result...")
        await self._step_record(think_result, act_result)

        # Step 6: LEARN - Store learning if applicable
        if act_result.should_learn and act_result.learning:
            await self.logger.log_learn(f"Storing learning: {act_result.learning[:50]}...")
            await self._step_learn(think_result, act_result)

        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        await self.logger.log_info(f"Cycle completed in {cycle_duration:.2f}s")

    # ==================== STEP IMPLEMENTATIONS ====================

    async def _step_read(self) -> Dict[str, Any]:
        """READ step: Get recent context from short-term memory."""
        context = await self.memory.get_recent_context()

        await self.memory.record_step(
            OrchestratorLogType.READ,
            f"Read context: active_goal={context.get('active_goal') is not None}, "
            f"pending={context.get('pending_goals_count', 0)}",
            context={"summary": context}
        )

        return context

    async def _step_query(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """QUERY step: Get relevant learnings from long-term memory."""
        learnings = []

        # Only query if we have an active goal
        active_goal = context.get("active_goal")
        if active_goal:
            goal_desc = active_goal.get("description", "")
            learnings = self.memory.query_relevant_learnings(goal_desc, limit=3)

            await self.memory.record_step(
                OrchestratorLogType.QUERY,
                f"Found {len(learnings)} relevant learnings for goal",
                goal_id=active_goal.get("id")
            )

        return learnings

    async def _step_think(
        self,
        context: Dict[str, Any],
        learnings: List[Dict[str, Any]]
    ) -> ThinkResult:
        """
        THINK step: Decide what action to take.

        Priority:
        1. VERIFY_LIMIT - Always check usage first
        2. CREATE_FIX - If there's a failed card that needs fixing
        3. EXECUTE_CARD - If there's a card ready to execute
        4. DECOMPOSE - If there's a new goal to break down
        5. COMPLETE_GOAL - If all cards are done
        6. WAIT - Nothing to do
        """
        # Priority 1: Check usage limits
        usage = await self.usage_checker.check_usage()
        self._last_usage_check = usage

        if not usage.is_safe_to_execute:
            return ThinkResult(
                decision=OrchestratorDecision.WAIT,
                reason=f"Usage limit exceeded: session={usage.session_used_percent}%, daily={usage.daily_used_percent}%"
            )

        # Get active goal
        active_goal = await self.goal_repo.get_active_goal()

        if active_goal:
            # Check if goal has cards
            card_ids = active_goal.cards or []

            if not card_ids:
                # Goal has no cards yet - decompose it
                return ThinkResult(
                    decision=OrchestratorDecision.DECOMPOSE,
                    goal_id=active_goal.id,
                    reason="Active goal has no cards, need to decompose"
                )

            # Check status of cards
            cards_status = await self._get_cards_status(card_ids)

            # Check for failed tests that need fix
            failed_cards = [c for c in cards_status if c.get("needs_fix")]
            if failed_cards:
                return ThinkResult(
                    decision=OrchestratorDecision.CREATE_FIX,
                    goal_id=active_goal.id,
                    card_id=failed_cards[0].get("id"),
                    reason=f"Card {failed_cards[0].get('id')[:8]} failed test, creating fix",
                    context={"error": failed_cards[0].get("error")}
                )

            # Check for cards ready to execute (in backlog or workflow columns)
            ready_cards = [c for c in cards_status if c.get("ready_to_execute")]
            if ready_cards:
                return ThinkResult(
                    decision=OrchestratorDecision.EXECUTE_CARD,
                    goal_id=active_goal.id,
                    card_id=ready_cards[0].get("id"),
                    reason=f"Card {ready_cards[0].get('id')[:8]} ready to execute"
                )

            # Check if all cards are done
            done_cards = [c for c in cards_status if c.get("column") in ["done", "completed"]]
            if len(done_cards) == len(cards_status):
                return ThinkResult(
                    decision=OrchestratorDecision.COMPLETE_GOAL,
                    goal_id=active_goal.id,
                    reason="All cards completed"
                )

            # Cards in progress, wait
            return ThinkResult(
                decision=OrchestratorDecision.WAIT,
                goal_id=active_goal.id,
                reason="Cards in progress, waiting"
            )

        # No active goal, check for pending goals
        pending_goals = await self.goal_repo.get_pending_goals()
        if pending_goals:
            # Activate first pending goal
            first_goal = pending_goals[0]
            await self.goal_repo.update_status(first_goal.id, GoalStatus.ACTIVE)
            return ThinkResult(
                decision=OrchestratorDecision.DECOMPOSE,
                goal_id=first_goal.id,
                reason=f"Activated pending goal: {first_goal.description[:50]}"
            )

        # Nothing to do
        return ThinkResult(
            decision=OrchestratorDecision.WAIT,
            reason="No active or pending goals"
        )

    async def _step_act(self, think_result: ThinkResult) -> ActResult:
        """ACT step: Execute the decided action."""
        try:
            match think_result.decision:
                case OrchestratorDecision.VERIFY_LIMIT:
                    return await self._act_verify_limit()

                case OrchestratorDecision.DECOMPOSE:
                    return await self._act_decompose(think_result.goal_id)

                case OrchestratorDecision.EXECUTE_CARD:
                    return await self._act_execute_card(think_result.card_id)

                case OrchestratorDecision.CREATE_FIX:
                    return await self._act_create_fix(
                        think_result.card_id,
                        think_result.context
                    )

                case OrchestratorDecision.COMPLETE_GOAL:
                    return await self._act_complete_goal(think_result.goal_id)

                case OrchestratorDecision.WAIT:
                    return ActResult(success=True, should_learn=False)

        except Exception as e:
            logger.exception(f"Error in ACT step: {e}")
            return ActResult(
                success=False,
                error=str(e)
            )

    async def _step_record(self, think_result: ThinkResult, act_result: ActResult) -> None:
        """RECORD step: Save result to short-term memory."""
        await self.memory.record_step(
            OrchestratorLogType.ACT,
            f"Action {think_result.decision.value}: success={act_result.success}",
            context={
                "decision": think_result.decision.value,
                "success": act_result.success,
                "error": act_result.error,
            },
            goal_id=think_result.goal_id
        )

        # Record action in database
        if think_result.goal_id:
            await self.action_repo.create(
                goal_id=think_result.goal_id,
                action_type=ActionType(think_result.decision.value),
                input_context=think_result.context,
                card_id=think_result.card_id,
            )

    async def _step_learn(self, think_result: ThinkResult, act_result: ActResult) -> None:
        """LEARN step: Store learning in long-term memory."""
        if not think_result.goal_id or not act_result.learning:
            return

        goal = await self.goal_repo.get_by_id(think_result.goal_id)
        if not goal:
            return

        # Store in Qdrant
        learning_id = self.memory.store_learning(
            goal_description=goal.description,
            learning=act_result.learning,
            cards_created=goal.cards or [],
            outcome="success" if act_result.success else "failed",
            error_encountered=act_result.error,
            tokens_used=goal.total_tokens,
            cost_usd=goal.total_cost_usd,
        )

        # Update goal with learning
        if learning_id:
            await self.goal_repo.set_learning(
                goal_id=goal.id,
                learning=act_result.learning,
                learning_id=learning_id
            )

        await self.memory.record_step(
            OrchestratorLogType.LEARN,
            f"Stored learning: {act_result.learning[:50]}...",
            goal_id=think_result.goal_id
        )

    # ==================== ACTION IMPLEMENTATIONS ====================

    async def _act_verify_limit(self) -> ActResult:
        """Verify Claude usage limits."""
        usage = await self.usage_checker.check_usage()
        return ActResult(
            success=True,
            data={"usage": usage.__dict__}
        )

    async def _act_decompose(self, goal_id: str) -> ActResult:
        """Decompose a goal into multiple cards using Claude Opus 4.5."""
        goal = await self.goal_repo.get_by_id(goal_id)
        if not goal:
            return ActResult(success=False, error="Goal not found")

        await self.logger.log_act(
            f"Decomposing goal with Opus 4.5: {goal.description[:50]}...",
            goal_id=goal_id
        )

        # Use AI to decompose the goal into multiple cards
        from .goal_decomposer_service import decompose_goal
        from ..schemas.card import CardCreate
        from pathlib import Path

        # Get project working directory
        from ..routes.projects import get_project_manager
        try:
            cwd = Path(get_project_manager().get_working_directory())
        except Exception:
            cwd = Path.cwd()

        # Call Opus 4.5 to decompose
        decomposition = await decompose_goal(
            goal_description=goal.description,
            cwd=cwd
        )

        if not decomposition.success:
            await self.logger.log_error(
                f"Decomposition failed: {decomposition.error}",
                goal_id=goal_id
            )
            return ActResult(
                success=False,
                error=decomposition.error or "Failed to decompose goal"
            )

        # Create cards from decomposition
        created_cards = []
        for decomposed_card in decomposition.cards:
            card_data = CardCreate(
                title=decomposed_card.title,
                description=decomposed_card.description,
            )

            card = await self.card_repo.create(card_data)
            created_cards.append(card.id)

            # Add card to goal
            await self.goal_repo.add_card(goal_id, card.id)

            await self.logger.log_act(
                f"Created card {len(created_cards)}/{len(decomposition.cards)}: {card.title[:40]}...",
                goal_id=goal_id,
                data={"card_id": card.id, "order": decomposed_card.order}
            )

        await self.logger.log_act(
            f"Decomposition complete: {len(created_cards)} cards created",
            goal_id=goal_id,
            data={
                "card_ids": created_cards,
                "reasoning": decomposition.reasoning
            }
        )

        return ActResult(
            success=True,
            data={
                "card_ids": created_cards,
                "card_count": len(created_cards),
                "reasoning": decomposition.reasoning
            }
        )

    async def _act_execute_card(self, card_id: str) -> ActResult:
        """Execute a card through the workflow."""
        card = await self.card_repo.get_by_id(card_id)
        if not card:
            return ActResult(success=False, error="Card not found")

        # Import execution functions
        from ..agent import execute_plan, execute_implement, execute_test_implementation, execute_review
        from pathlib import Path

        # Get project path
        cwd = str(Path.cwd())

        try:
            # Determine what stage to execute based on card column
            column = card.column_id

            if column == "backlog":
                # Move to plan and execute plan
                await self.card_repo.move(card_id, "plan")
                result = await execute_plan(
                    card_id=card_id,
                    title=card.title,
                    description=card.description or "",
                    cwd=cwd,
                    model=card.model_plan,
                )

                if result.success:
                    await self.card_repo.move(card_id, "implement")

            elif column == "implement":
                # Execute implement
                result = await execute_implement(
                    card_id=card_id,
                    spec_path=card.spec_path or "",
                    cwd=cwd,
                    model=card.model_implement,
                )

                if result.success:
                    await self.card_repo.move(card_id, "test")

            elif column == "test":
                # Execute test
                result = await execute_test_implementation(
                    card_id=card_id,
                    spec_path=card.spec_path or "",
                    cwd=cwd,
                    model=card.model_test,
                )

                if result.success:
                    await self.card_repo.move(card_id, "review")
                else:
                    # Test failed - might need fix card
                    return ActResult(
                        success=False,
                        error=result.error,
                        data={"needs_fix": True}
                    )

            elif column == "review":
                # Execute review
                result = await execute_review(
                    card_id=card_id,
                    spec_path=card.spec_path or "",
                    cwd=cwd,
                    model=card.model_review,
                )

                if result.success:
                    await self.card_repo.move(card_id, "done")

            else:
                return ActResult(
                    success=True,
                    data={"message": f"Card in {column}, no action needed"}
                )

            return ActResult(
                success=result.success,
                error=result.error if not result.success else None,
                data={"column": card.column_id}
            )

        except Exception as e:
            logger.exception(f"Error executing card {card_id}: {e}")
            return ActResult(success=False, error=str(e))

    async def _act_create_fix(self, card_id: str, context: Optional[dict]) -> ActResult:
        """Create a fix card for a failed card."""
        error_info = {
            "description": f"Fix for test failure",
            "context": context.get("error") if context else "",
        }

        fix_card = await self.card_repo.create_fix_card(card_id, error_info)

        if fix_card:
            return ActResult(
                success=True,
                data={"fix_card_id": fix_card.id}
            )

        return ActResult(
            success=False,
            error="Failed to create fix card"
        )

    async def _act_complete_goal(self, goal_id: str) -> ActResult:
        """Complete a goal and extract learning."""
        goal = await self.goal_repo.get_by_id(goal_id)
        if not goal:
            return ActResult(success=False, error="Goal not found")

        # Update goal status
        await self.goal_repo.update_status(goal_id, GoalStatus.COMPLETED)

        # Extract learning
        # TODO: Use AI to generate learning from goal execution
        learning = f"Completed goal: {goal.description}. Cards: {len(goal.cards or [])}."

        return ActResult(
            success=True,
            should_learn=True,
            learning=learning,
            data={"cards_completed": len(goal.cards or [])}
        )

    # ==================== HELPERS ====================

    async def _get_cards_status(self, card_ids: List[str]) -> List[Dict[str, Any]]:
        """Get status of multiple cards."""
        statuses = []

        for card_id in card_ids:
            card = await self.card_repo.get_by_id(card_id)
            if not card:
                continue

            status = {
                "id": card.id,
                "title": card.title,
                "column": card.column_id,
                "ready_to_execute": card.column_id in ["backlog", "plan", "implement", "test", "review"],
                "needs_fix": False,  # TODO: Detect test failures
            }
            statuses.append(status)

        return statuses

    # ==================== PUBLIC API ====================

    async def submit_goal(
        self,
        description: str,
        source: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a new goal to the orchestrator."""
        goal = await self.goal_repo.create(
            description=description,
            source=source,
            source_id=source_id,
        )

        await self.logger.log_info(
            f"New goal submitted: {description[:50]}...",
            goal_id=goal.id
        )

        return {
            "id": goal.id,
            "description": goal.description,
            "status": goal.status.value,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "running": self._running,
            "loop_interval_seconds": self.settings.orchestrator_loop_interval_seconds,
            "usage_limit_percent": self.settings.orchestrator_usage_limit_percent,
            "last_usage_check": self._last_usage_check.__dict__ if self._last_usage_check else None,
            "memory_health": self.memory.health_check(),
        }


# Global instance holder
_orchestrator_service: Optional[OrchestratorService] = None


def get_orchestrator_service(session: AsyncSession) -> OrchestratorService:
    """Get or create orchestrator service."""
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService(session)
    return _orchestrator_service

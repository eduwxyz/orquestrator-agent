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
from .live_broadcast_service import get_live_broadcast_service

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

logger = logging.getLogger(__name__)


class OrchestratorDecision(str, Enum):
    """Decisions the orchestrator can make."""
    VERIFY_LIMIT = "verify_limit"
    DECOMPOSE = "decompose"
    EXECUTE_CARD = "execute_card"
    EXECUTE_CARDS_PARALLEL = "execute_cards_parallel"  # Execute multiple cards in parallel
    CREATE_FIX = "create_fix"
    WAIT = "wait"
    COMPLETE_GOAL = "complete_goal"


@dataclass
class ThinkResult:
    """Result of the THINK step."""
    decision: OrchestratorDecision
    goal_id: Optional[str] = None
    card_ids: Optional[List[str]] = None  # List of cards for parallel execution
    reason: str = ""
    context: Optional[Dict[str, Any]] = None

    @property
    def card_id(self) -> Optional[str]:
        """Backward compatibility: return first card_id."""
        return self.card_ids[0] if self.card_ids else None


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

    def __init__(self):
        self.settings = get_settings()
        self.usage_checker = get_usage_checker_service(self.settings.orchestrator_usage_limit_percent)
        self.logger = get_orchestrator_logger(self.settings.orchestrator_log_file)

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_usage_check: Optional[UsageInfo] = None

    def _get_session_factory(self):
        """Get the current session factory from db_manager or fallback to legacy."""
        from ..database import get_session
        return get_session()

    def _create_repos(self, session: AsyncSession):
        """Create repository instances with a fresh session."""
        return {
            "goal_repo": GoalRepository(session),
            "action_repo": ActionRepository(session),
            "log_repo": LogRepository(session, self.settings.short_term_memory_retention_hours),
            "card_repo": CardRepository(session),
            "memory": MemoryService(session, self.settings.short_term_memory_retention_hours),
        }

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
        """Main orchestrator loop with retry for database locks."""
        while self._running:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self._execute_cycle()
                    break  # Success, exit retry loop
                except Exception as e:
                    error_str = str(e)
                    if "database is locked" in error_str and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 3  # 3s, 6s, 9s
                        logger.warning(f"[Orchestrator] DB locked, retry {attempt + 1}/{max_retries} in {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.exception(f"[Orchestrator] Error in loop: {e}")
                        try:
                            await self.logger.log_error(f"Loop error: {e}")
                        except Exception:
                            pass  # Don't fail if logging fails
                        break

            # Wait for next cycle
            await asyncio.sleep(self.settings.orchestrator_loop_interval_seconds)

    # ==================== MAIN CYCLE ====================

    async def _execute_cycle(self) -> None:
        """Execute one cycle of the orchestrator loop."""
        cycle_start = datetime.utcnow()
        await self.logger.log_info(f"Starting cycle at {cycle_start.isoformat()}")

        # Notify live spectators that AI is working
        live_broadcast = get_live_broadcast_service()
        await live_broadcast.update_status(is_working=True, current_stage="thinking")
        await live_broadcast.broadcast_log("Orchestrator starting new cycle...", "info")

        # Get fresh session for this cycle (uses current project's database)
        session_factory = self._get_session_factory()

        async with session_factory() as session:
            try:
                # Create repos with fresh session
                repos = self._create_repos(session)

                # Step 1: READ - Get recent context
                await self.logger.log_read("Reading short-term memory...")
                await live_broadcast.broadcast_log("📖 Reading context...", "info")
                context = await self._step_read(repos)

                # Step 2: QUERY - Get relevant learnings
                await self.logger.log_query("Querying long-term memory...")
                learnings = await self._step_query(context, repos)

                # Step 3: THINK - Decide action
                await self.logger.log_think("Deciding next action...")
                await live_broadcast.broadcast_log("🧠 Thinking about next action...", "info")
                think_result = await self._step_think(context, learnings, repos)
                await self.logger.log_think(
                    f"Decision: {think_result.decision.value} - {think_result.reason}",
                    goal_id=think_result.goal_id
                )
                # Broadcast decision to live spectators
                await live_broadcast.broadcast_log(
                    f"💡 Decision: {think_result.decision.value} - {think_result.reason}",
                    "info"
                )

                # Step 4: ACT - Execute decision
                await self.logger.log_act(f"Executing {think_result.decision.value}...")
                await live_broadcast.broadcast_log(
                    f"⚡ Executing: {think_result.decision.value}...",
                    "info"
                )
                act_result = await self._step_act(think_result, repos)

                # Broadcast result
                if act_result.success:
                    if act_result.data:
                        data_summary = str(act_result.data)[:100]
                        await live_broadcast.broadcast_log(f"✅ Success: {data_summary}", "success")
                else:
                    await live_broadcast.broadcast_log(f"❌ Failed: {act_result.error}", "error")

                # Step 5: RECORD - Save to short-term memory
                await self.logger.log_record("Recording result...")
                await self._step_record(think_result, act_result, repos)

                # Step 6: LEARN - Store learning if applicable
                if act_result.should_learn and act_result.learning:
                    await self.logger.log_learn(f"Storing learning: {act_result.learning[:50]}...")
                    await live_broadcast.broadcast_log(f"📚 Learning: {act_result.learning[:80]}...", "info")
                    await self._step_learn(think_result, act_result, repos)

                await session.commit()

            except Exception as e:
                await session.rollback()
                await live_broadcast.broadcast_log(f"Cycle error: {str(e)}", "error")
                raise

        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        await self.logger.log_info(f"Cycle completed in {cycle_duration:.2f}s")
        await live_broadcast.broadcast_log(f"Cycle completed in {cycle_duration:.2f}s", "success")

    # ==================== STEP IMPLEMENTATIONS ====================

    async def _step_read(self, repos: Dict[str, Any]) -> Dict[str, Any]:
        """READ step: Get recent context from short-term memory."""
        memory = repos["memory"]
        context = await memory.get_recent_context()

        await memory.record_step(
            OrchestratorLogType.READ,
            f"Read context: active_goal={context.get('active_goal') is not None}, "
            f"pending={context.get('pending_goals_count', 0)}",
            context={"summary": context}
        )

        return context

    async def _step_query(self, context: Dict[str, Any], repos: Dict[str, Any]) -> List[Dict[str, Any]]:
        """QUERY step: Get relevant learnings from long-term memory."""
        memory = repos["memory"]
        learnings = []

        # Only query if we have an active goal
        active_goal = context.get("active_goal")
        if active_goal:
            goal_desc = active_goal.get("description", "")
            learnings = memory.query_relevant_learnings(goal_desc, limit=3)

            await memory.record_step(
                OrchestratorLogType.QUERY,
                f"Found {len(learnings)} relevant learnings for goal",
                goal_id=active_goal.get("id")
            )

        return learnings

    async def _step_think(
        self,
        context: Dict[str, Any],
        learnings: List[Dict[str, Any]],
        repos: Dict[str, Any]
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
        goal_repo = repos["goal_repo"]
        card_repo = repos["card_repo"]

        # Priority 1: Check usage limits
        usage = await self.usage_checker.check_usage()
        self._last_usage_check = usage

        if not usage.is_safe_to_execute:
            return ThinkResult(
                decision=OrchestratorDecision.WAIT,
                reason=f"Usage limit exceeded: session={usage.session_used_percent}%, daily={usage.daily_used_percent}%"
            )

        # Get active goal
        active_goal = await goal_repo.get_active_goal()

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
            cards_status = await self._get_cards_status(card_ids, card_repo)

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

            # Check for cards ready to execute (in backlog or workflow columns with satisfied deps)
            ready_cards = [c for c in cards_status if c.get("ready_to_execute")]
            if ready_cards:
                # Execute one card at a time to avoid SQLAlchemy session conflicts
                first_card_id = ready_cards[0].get("id")
                return ThinkResult(
                    decision=OrchestratorDecision.EXECUTE_CARD,
                    goal_id=active_goal.id,
                    card_ids=[first_card_id],
                    reason=f"Card {first_card_id[:8]} ready to execute ({len(ready_cards)} cards waiting)"
                )

                # NOTE: Parallel execution disabled due to SQLAlchemy session conflicts
                # TODO: Fix session management to re-enable parallel execution

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
        pending_goals = await goal_repo.get_pending_goals()
        if pending_goals:
            # Activate first pending goal
            first_goal = pending_goals[0]
            await goal_repo.update_status(first_goal.id, GoalStatus.ACTIVE)
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

    async def _step_act(self, think_result: ThinkResult, repos: Dict[str, Any]) -> ActResult:
        """ACT step: Execute the decided action."""
        try:
            match think_result.decision:
                case OrchestratorDecision.VERIFY_LIMIT:
                    return await self._act_verify_limit()

                case OrchestratorDecision.DECOMPOSE:
                    return await self._act_decompose(think_result.goal_id, repos)

                case OrchestratorDecision.EXECUTE_CARD:
                    return await self._act_execute_card(think_result.card_id, repos)

                case OrchestratorDecision.EXECUTE_CARDS_PARALLEL:
                    return await self._act_execute_cards_parallel(think_result.card_ids, repos)

                case OrchestratorDecision.CREATE_FIX:
                    return await self._act_create_fix(
                        think_result.card_id,
                        think_result.context,
                        repos
                    )

                case OrchestratorDecision.COMPLETE_GOAL:
                    return await self._act_complete_goal(think_result.goal_id, repos)

                case OrchestratorDecision.WAIT:
                    return ActResult(success=True, should_learn=False)

        except Exception as e:
            logger.exception(f"Error in ACT step: {e}")
            return ActResult(
                success=False,
                error=str(e)
            )

    async def _step_record(self, think_result: ThinkResult, act_result: ActResult, repos: Dict[str, Any]) -> None:
        """RECORD step: Save result to short-term memory."""
        memory = repos["memory"]
        action_repo = repos["action_repo"]

        await memory.record_step(
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
            await action_repo.create(
                goal_id=think_result.goal_id,
                action_type=ActionType(think_result.decision.value),
                input_context=think_result.context,
                card_id=think_result.card_id,
            )

    async def _step_learn(self, think_result: ThinkResult, act_result: ActResult, repos: Dict[str, Any]) -> None:
        """LEARN step: Store learning in long-term memory."""
        if not think_result.goal_id or not act_result.learning:
            return

        goal_repo = repos["goal_repo"]
        memory = repos["memory"]

        goal = await goal_repo.get_by_id(think_result.goal_id)
        if not goal:
            return

        # Store in Qdrant
        learning_id = memory.store_learning(
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
            await goal_repo.set_learning(
                goal_id=goal.id,
                learning=act_result.learning,
                learning_id=learning_id
            )

        await memory.record_step(
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

    async def _act_decompose(self, goal_id: str, repos: Dict[str, Any]) -> ActResult:
        """Decompose a goal into multiple cards using Claude Opus 4.5."""
        goal_repo = repos["goal_repo"]
        card_repo = repos["card_repo"]

        goal = await goal_repo.get_by_id(goal_id)
        if not goal:
            return ActResult(success=False, error="Goal not found")

        await self.logger.log_act(
            f"Decomposing goal with Opus 4.5: {goal.description[:50]}...",
            goal_id=goal_id
        )

        # Broadcast to live spectators
        live_broadcast = get_live_broadcast_service()
        await live_broadcast.broadcast_agent_status("orchestrator", "working", "Analisando objetivo...")
        await live_broadcast.broadcast_log(
            f"🤖 AI analyzing goal with Opus 4.5...",
            "info"
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
            await live_broadcast.broadcast_log(
                f"❌ Decomposition failed: {decomposition.error}",
                "error"
            )
            return ActResult(
                success=False,
                error=decomposition.error or "Failed to decompose goal"
            )

        # Broadcast decomposition result
        await live_broadcast.broadcast_log(
            f"🎯 AI planned {len(decomposition.cards)} tasks to complete the goal",
            "success"
        )

        # First pass: Create all cards and build order-to-ID mapping
        created_cards = []
        order_to_id: Dict[int, str] = {}

        for decomposed_card in decomposition.cards:
            card_data = CardCreate(
                title=decomposed_card.title,
                description=decomposed_card.description,
                dependencies=[],  # Will be set in second pass
            )

            card = await card_repo.create(card_data)
            created_cards.append(card.id)
            order_to_id[decomposed_card.order] = card.id

            # Add card to goal
            await goal_repo.add_card(goal_id, card.id)

            # Broadcast card creation via WebSocket
            try:
                from .card_ws import card_ws_manager
                from ..schemas.card import CardResponse

                card_response = CardResponse.model_validate(card)
                card_dict = card_response.model_dump(by_alias=True, mode='json')
                await card_ws_manager.broadcast_card_created(
                    card_id=card.id,
                    card_data=card_dict
                )
            except Exception as e:
                logger.warning(f"Failed to broadcast card creation: {e}")

            await self.logger.log_act(
                f"Created card {len(created_cards)}/{len(decomposition.cards)}: {card.title[:40]}...",
                goal_id=goal_id,
                data={"card_id": card.id, "order": decomposed_card.order}
            )

            # Broadcast card creation to live spectators
            await live_broadcast.broadcast_log(
                f"📋 Card {len(created_cards)}/{len(decomposition.cards)}: {card.title}",
                "info"
            )

        # Second pass: Update cards with resolved dependency IDs
        for decomposed_card in decomposition.cards:
            if decomposed_card.dependencies:
                card_id = order_to_id.get(decomposed_card.order)
                if card_id:
                    # Map order indices to actual card IDs
                    resolved_deps = [
                        order_to_id[dep_order]
                        for dep_order in decomposed_card.dependencies
                        if dep_order in order_to_id
                    ]
                    if resolved_deps:
                        await card_repo.update_dependencies(card_id, resolved_deps)
                        await self.logger.log_act(
                            f"Set dependencies for card {card_id[:8]}: {len(resolved_deps)} deps",
                            goal_id=goal_id,
                            data={"card_id": card_id, "dependencies": resolved_deps}
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

    async def _act_execute_card(self, card_id: str, repos: Dict[str, Any]) -> ActResult:
        """Execute a card through simplified workflow (plan → implement → done) for live showcase."""
        card_repo = repos["card_repo"]
        live_broadcast = get_live_broadcast_service()

        card = await card_repo.get_by_id(card_id)
        if not card:
            return ActResult(success=False, error="Card not found")

        # Import execution functions
        from ..agent import execute_plan, execute_implement
        from pathlib import Path

        # Get project path from project manager
        from ..routes.projects import get_project_manager
        try:
            cwd = get_project_manager().get_working_directory()
        except Exception:
            cwd = str(Path.cwd())

        current_column = card.column_id

        # If already done, nothing to do
        if current_column == "done":
            return ActResult(
                success=True,
                data={"message": "Card already completed"}
            )

        await self.logger.log_act(
            f"Starting workflow for card {card_id[:8]} from {current_column}",
            goal_id=None,
            data={"card_id": card_id, "starting_column": current_column}
        )

        try:
            # Stage 1: PLAN
            if current_column in ["backlog", "plan"]:
                # Broadcast: Planner agent working
                await live_broadcast.broadcast_agent_status("planner", "working", "Planejando o projeto...")
                await live_broadcast.update_status(is_working=True, current_stage="planning", progress=10)

                await self.logger.log_act(f"[1/2] Executing PLAN stage...")
                await self._move_card_with_broadcast(card_id, "plan", card_repo)

                result = await execute_plan(
                    card_id=card_id,
                    title=card.title,
                    description=card.description or "",
                    cwd=cwd,
                    model=card.model_plan,
                )

                if not result.success:
                    await live_broadcast.broadcast_agent_status("planner", "error", result.error)
                    await self.logger.log_error(f"PLAN failed: {result.error}")
                    return ActResult(success=False, error=f"Plan failed: {result.error}")

                await self.logger.log_act(f"[1/2] PLAN completed successfully")
                await live_broadcast.broadcast_agent_status("planner", "idle", None)
                await live_broadcast.update_status(is_working=True, current_stage="planning", progress=40)

                # Save spec_path to card
                if result.spec_path:
                    await card_repo.update_spec_path(card_id, result.spec_path)
                    await self.logger.log_act(f"Saved spec_path: {result.spec_path}")

                # Refresh card to get updated spec_path
                card = await card_repo.get_by_id(card_id)

            # Stage 2: IMPLEMENT
            if current_column in ["backlog", "plan", "implement"]:
                if not card.spec_path:
                    await self.logger.log_error(f"Cannot execute IMPLEMENT: card has no spec_path")
                    return ActResult(success=False, error="Card has no spec_path. Run /plan first.")

                # Broadcast: Coder agent working
                await live_broadcast.broadcast_agent_status("coder", "working", "Implementando o código...")
                await live_broadcast.update_status(is_working=True, current_stage="implementing", progress=50)

                await self.logger.log_act(f"[2/2] Executing IMPLEMENT stage...")
                await self._move_card_with_broadcast(card_id, "implement", card_repo)

                result = await execute_implement(
                    card_id=card_id,
                    spec_path=card.spec_path,
                    cwd=cwd,
                    model=card.model_implement,
                )

                if not result.success:
                    await live_broadcast.broadcast_agent_status("coder", "error", result.error)
                    await self.logger.log_error(f"IMPLEMENT failed: {result.error}")
                    return ActResult(success=False, error=f"Implement failed: {result.error}")

                await self.logger.log_act(f"[2/2] IMPLEMENT completed successfully")
                await live_broadcast.broadcast_agent_status("coder", "idle", None)
                await live_broadcast.update_status(is_working=True, current_stage="implementing", progress=90)

            # Move directly to done (skip test/review for live showcase)
            print(f"[DEBUG] About to move card {card_id[:8]} to done")
            moved_card, move_error = await self._move_card_with_broadcast(card_id, "done", card_repo)
            print(f"[DEBUG] Move result: card={moved_card is not None}, error={move_error}")

            if move_error:
                print(f"[DEBUG] Move failed with error: {move_error}")
                await self.logger.log_error(f"Failed to move card to done: {move_error}")
                return ActResult(success=False, error=f"Failed to move to done: {move_error}")

            # CRITICAL: Commit immediately to ensure next cycle sees the change
            print(f"[DEBUG] Committing session...")
            await card_repo.session.commit()
            print(f"[DEBUG] Commit done, verifying card column...")

            # Verify the move worked
            verify_card = await card_repo.get_by_id(card_id)
            print(f"[DEBUG] Card column after commit: {verify_card.column_id if verify_card else 'NOT FOUND'}")

            await live_broadcast.update_status(is_working=True, current_stage="completed", progress=100)

            await self.logger.log_act(
                f"Workflow completed for card {card_id[:8]}",
                goal_id=None,
                data={"card_id": card_id, "final_column": "done"}
            )

            return ActResult(
                success=True,
                should_learn=True,
                learning=f"Successfully completed workflow for card: {card.title}",
                data={"column": "done", "workflow_completed": True}
            )

        except Exception as e:
            logger.exception(f"Error executing card {card_id}: {e}")
            return ActResult(success=False, error=str(e))

    async def _act_execute_cards_parallel(
        self,
        card_ids: List[str],
        repos: Dict[str, Any]
    ) -> ActResult:
        """Execute multiple cards in parallel."""
        await self.logger.log_act(
            f"Starting parallel execution of {len(card_ids)} cards",
            data={"card_ids": [cid[:8] for cid in card_ids]}
        )

        # Create tasks for all cards
        tasks = [
            self._act_execute_card(card_id, repos)
            for card_id in card_ids
        ]

        # Execute all tasks in parallel using asyncio.gather
        # return_exceptions=True prevents one failure from canceling others
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successes = []
        failures = []

        for card_id, result in zip(card_ids, results):
            if isinstance(result, Exception):
                failures.append({
                    "card_id": card_id,
                    "error": str(result)
                })
                await self.logger.log_error(
                    f"Card {card_id[:8]} failed with exception: {result}"
                )
            elif isinstance(result, ActResult):
                if result.success:
                    successes.append(card_id)
                else:
                    failures.append({
                        "card_id": card_id,
                        "error": result.error
                    })
                    await self.logger.log_error(
                        f"Card {card_id[:8]} failed: {result.error}"
                    )

        await self.logger.log_act(
            f"Parallel execution completed: {len(successes)} succeeded, {len(failures)} failed",
            data={"successes": [s[:8] for s in successes], "failures": failures}
        )

        # Determine overall success (partial success is still success for the orchestrator)
        all_success = len(failures) == 0

        return ActResult(
            success=all_success,
            should_learn=len(successes) > 0,
            learning=f"Parallel execution: {len(successes)}/{len(card_ids)} cards completed" if successes else None,
            error=f"{len(failures)} cards failed" if failures else None,
            data={
                "successes": successes,
                "failures": failures,
                "total": len(card_ids)
            }
        )

    async def _act_create_fix(self, card_id: str, context: Optional[dict], repos: Dict[str, Any]) -> ActResult:
        """Create a fix card for a failed card."""
        card_repo = repos["card_repo"]

        error_info = {
            "description": f"Fix for test failure",
            "context": context.get("error") if context else "",
        }

        fix_card = await card_repo.create_fix_card(card_id, error_info)

        if fix_card:
            return ActResult(
                success=True,
                data={"fix_card_id": fix_card.id}
            )

        return ActResult(
            success=False,
            error="Failed to create fix card"
        )

    async def _act_complete_goal(self, goal_id: str, repos: Dict[str, Any]) -> ActResult:
        """Complete a goal and extract learning, then start voting for next project."""
        goal_repo = repos["goal_repo"]

        goal = await goal_repo.get_by_id(goal_id)
        if not goal:
            return ActResult(success=False, error="Goal not found")

        # Update goal status
        await goal_repo.update_status(goal_id, GoalStatus.COMPLETED)

        # Extract learning
        learning = f"Completed goal: {goal.description}. Cards: {len(goal.cards or [])}."

        # Broadcast completion to live spectators
        live_broadcast = get_live_broadcast_service()
        await live_broadcast.broadcast_log("🎉 Projeto concluído!", "success")
        await live_broadcast.update_status(is_working=False, current_stage="completed")

        # For live_mode goals: save to gallery and start voting
        if goal.source in ["live_mode", "live_mode_voting"]:
            # Longer delay to ensure previous transaction is fully committed (avoid DB locked)
            await asyncio.sleep(3)
            # Create CompletedProject for gallery
            await self._save_completed_project(goal)
            # Another delay before voting (avoid DB locked)
            await asyncio.sleep(3)
            # Start voting for next project
            await self._start_voting_for_next_project()

        return ActResult(
            success=True,
            should_learn=True,
            learning=learning,
            data={"cards_completed": len(goal.cards or [])}
        )

    async def _save_completed_project(self, goal) -> None:
        """Save completed project to gallery with retry logic."""
        from uuid import uuid4
        from ..models.live import CompletedProject
        from ..database import async_session_maker

        live_broadcast = get_live_broadcast_service()

        # Parse source_id: "folder|title|category"
        if not goal.source_id:
            logger.warning("Goal has no source_id, skipping gallery save")
            return

        parts = goal.source_id.split("|")
        project_folder = parts[0] if len(parts) > 0 else "unknown"
        project_title = parts[1] if len(parts) > 1 else "Projeto"
        project_category = parts[2] if len(parts) > 2 else None

        # Retry logic for SQLite locks
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with async_session_maker() as session:
                    completed = CompletedProject(
                        id=str(uuid4()),
                        title=project_title,
                        description=goal.description[:500] if goal.description else None,
                        category=project_category,
                        preview_url=f"/projects/{project_folder}/index.html",
                        screenshot_url=None,
                        like_count=0,
                        card_id=goal.cards[0] if goal.cards else None,
                    )
                    session.add(completed)
                    await session.commit()

                    logger.info(f"[Orchestrator] Saved to gallery: {project_title}")
                    await live_broadcast.broadcast_log(
                        f"📸 Projeto adicionado à galeria: {project_title}",
                        "success"
                    )

                    # Broadcast new project to gallery
                    await live_broadcast.broadcast({
                        "type": "project_added",
                        "project": {
                            "id": completed.id,
                            "title": completed.title,
                            "preview_url": completed.preview_url,
                            "like_count": 0
                        }
                    })
                    return  # Success, exit retry loop

            except Exception as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"[Orchestrator] DB locked, retrying in {(attempt + 1) * 2}s...")
                    await asyncio.sleep((attempt + 1) * 2)
                else:
                    logger.exception(f"[Orchestrator] Failed to save to gallery: {e}")
                    await live_broadcast.broadcast_log(f"⚠️ Erro ao salvar na galeria: {e}", "error")
                    return

    async def _start_voting_for_next_project(self) -> None:
        """Start a voting round with AI-generated project suggestions."""
        from .voting_service import get_voting_service
        from ..database import async_session_maker

        live_broadcast = get_live_broadcast_service()
        voting_service = get_voting_service()

        # Check if voting is already active
        if voting_service.is_active:
            logger.warning("Voting already active, skipping auto-start")
            return

        # Generate AI suggestions for next project
        await live_broadcast.broadcast_log("🤖 AI gerando sugestões de projetos...", "info")
        voting_options = await self._generate_ai_project_suggestions()

        if not voting_options:
            # Fallback to default options
            voting_options = [
                {"title": "🐍 Jogo da Cobrinha", "description": "Snake game clássico com visual neon", "category": "snake"},
                {"title": "🧮 Calculadora", "description": "Calculadora com design moderno", "category": "calculator"},
                {"title": "🎮 Quiz Interativo", "description": "Quiz de perguntas e respostas", "category": "quiz"},
            ]

        # Broadcast that voting is starting
        await live_broadcast.broadcast_log("⏳ Votação começa em 3 segundos...", "info")
        await asyncio.sleep(3)

        # Retry logic for SQLite locks
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with async_session_maker() as session:
                    voting_round, options = await voting_service.start_round(
                        db=session,
                        duration_seconds=60,  # 60 seconds for voting
                        options=voting_options
                    )

                    # Broadcast voting started
                    await live_broadcast.broadcast_voting_started(
                        options=[
                            {"id": o.id, "title": o.title, "description": o.description, "vote_count": 0}
                            for o in options
                        ],
                        ends_at=voting_round.ends_at.isoformat(),
                        duration_seconds=60
                    )

                    await live_broadcast.broadcast_log("🗳️ VOTE AGORA! 60 segundos!", "success")
                    logger.info(f"[Orchestrator] Auto-started voting with {len(options)} options")
                    return  # Success, exit retry loop

            except Exception as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"[Orchestrator] DB locked for voting, retrying in {(attempt + 1) * 2}s...")
                    await asyncio.sleep((attempt + 1) * 2)
                else:
                    logger.exception(f"[Orchestrator] Failed to start voting: {e}")
                    await live_broadcast.broadcast_log(f"❌ Erro ao iniciar votação: {e}", "error")
                    return

    async def _generate_ai_project_suggestions(self) -> list[dict]:
        """Use AI to generate creative project suggestions using Claude Agent SDK."""
        import json
        import re

        prompt = """Gere 3 sugestões criativas de mini-projetos web para uma live de programação.

Requisitos:
- Projetos simples que podem ser feitos em 1 arquivo HTML/CSS/JS
- Visuais e interativos
- Divertidos para uma audiência assistir sendo criados

Retorne APENAS um JSON array no formato:
[
  {"title": "🎮 Título", "description": "Descrição curta", "category": "identificador"},
  ...
]

Seja criativo! Exemplos de categorias: game, tool, animation, quiz, art, simulator."""

        try:
            options = ClaudeAgentOptions(
                cwd="/opt/zenflow",
                setting_sources=["user", "project"],
                allowed_tools=[],  # No tools needed, just text generation
                permission_mode="acceptEdits",
                model="haiku",  # Fast model for simple task
                max_tokens=500,
            )

            # Collect response
            full_response = ""
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text

            # Parse response
            content = full_response
            # Extract JSON from response (might be wrapped in markdown)
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            elif "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            suggestions = json.loads(content.strip())
            logger.info(f"[Orchestrator] AI generated {len(suggestions)} project suggestions")
            return suggestions[:3]  # Ensure max 3

        except Exception as e:
            logger.warning(f"[Orchestrator] Failed to generate AI suggestions: {e}")
            return []

    # ==================== HELPERS ====================

    async def _get_cards_status(self, card_ids: List[str], card_repo: CardRepository) -> List[Dict[str, Any]]:
        """Get status of multiple cards including dependency satisfaction."""
        # First pass: get all cards
        cards: Dict[str, Card] = {}
        for card_id in card_ids:
            card = await card_repo.get_by_id(card_id)
            if card:
                cards[card_id] = card

        # Second pass: build status with dependency checking
        statuses = []
        for card_id in card_ids:
            card = cards.get(card_id)
            if not card:
                continue

            # Check if dependencies are satisfied (all deps must be in 'done' column)
            deps = card.dependencies or []
            deps_satisfied = all(
                cards.get(dep_id) and cards.get(dep_id).column_id == "done"
                for dep_id in deps
            )

            # Card is ready to execute if:
            # 1. It's in an executable column
            # 2. All its dependencies are satisfied (in 'done')
            is_executable_column = card.column_id in ["backlog", "plan", "implement", "test", "review"]
            ready_to_execute = is_executable_column and deps_satisfied

            status = {
                "id": card.id,
                "title": card.title,
                "column": card.column_id,
                "dependencies": deps,
                "dependencies_satisfied": deps_satisfied,
                "ready_to_execute": ready_to_execute,
                "needs_fix": False,  # TODO: Detect test failures
            }
            statuses.append(status)

        return statuses

    async def _move_card_with_broadcast(
        self,
        card_id: str,
        to_column: str,
        card_repo: CardRepository
    ) -> tuple[Optional[Card], Optional[str]]:
        """Move a card and broadcast the change via WebSocket."""
        # Get current card state before move
        card = await card_repo.get_by_id(card_id)
        if not card:
            return None, "Card not found"

        from_column = card.column_id

        # Perform the move
        card, error = await card_repo.move(card_id, to_column)
        if error:
            return None, error

        # Broadcast via WebSocket (admin)
        try:
            from .card_ws import card_ws_manager
            from ..schemas.card import CardResponse

            card_response = CardResponse.model_validate(card)
            card_dict = card_response.model_dump(by_alias=True, mode='json')
            await card_ws_manager.broadcast_card_moved(
                card_id=card_id,
                from_column=from_column,
                to_column=to_column,
                card_data=card_dict
            )
        except Exception as e:
            # Don't fail the move if broadcast fails
            logger.warning(f"Failed to broadcast card move: {e}")

        # Broadcast to live spectators
        try:
            live_broadcast = get_live_broadcast_service()
            await live_broadcast.broadcast_card_moved(
                card={
                    "id": card.id,
                    "title": card.title,
                    "description": card.description,
                    "created_at": card.created_at
                },
                from_column=from_column,
                to_column=to_column
            )
            # Update status with current card
            stage_map = {"plan": "planning", "implement": "implementing", "test": "testing", "review": "reviewing"}
            stage = stage_map.get(to_column)
            await live_broadcast.update_status(
                is_working=True,
                current_stage=stage,
                current_card={"id": card.id, "title": card.title},
                progress=None
            )
            await live_broadcast.broadcast_log(f"Card '{card.title}' moved to {to_column}", "info")
        except Exception as e:
            logger.warning(f"Failed to broadcast to live: {e}")

        return card, None

    # ==================== PUBLIC API ====================

    async def submit_goal(
        self,
        description: str,
        source: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a new goal to the orchestrator."""
        # Get fresh session for this operation
        session_factory = self._get_session_factory()

        async with session_factory() as session:
            goal_repo = GoalRepository(session)
            goal = await goal_repo.create(
                description=description,
                source=source,
                source_id=source_id,
            )
            await session.commit()

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
        }


# Global instance holder
_orchestrator_service: Optional[OrchestratorService] = None


def get_orchestrator_service(session: Optional[AsyncSession] = None) -> OrchestratorService:
    """Get or create orchestrator service.

    Note: session parameter is kept for backward compatibility but is no longer used.
    The service now obtains fresh sessions from db_manager for each operation.
    """
    global _orchestrator_service
    if _orchestrator_service is None:
        _orchestrator_service = OrchestratorService()
    return _orchestrator_service

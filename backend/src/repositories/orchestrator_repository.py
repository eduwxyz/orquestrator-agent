"""Repository for orchestrator database operations."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.orchestrator import (
    Goal, GoalStatus,
    OrchestratorAction, ActionType,
    OrchestratorLog, OrchestratorLogType
)


class GoalRepository:
    """Repository for Goal database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, include_completed: bool = False) -> List[Goal]:
        """Get all goals, optionally including completed ones."""
        query = select(Goal).options(selectinload(Goal.actions))

        if not include_completed:
            query = query.where(Goal.status.notin_([GoalStatus.COMPLETED, GoalStatus.FAILED]))

        query = query.order_by(Goal.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID with its actions."""
        result = await self.session.execute(
            select(Goal)
            .options(selectinload(Goal.actions))
            .where(Goal.id == goal_id)
        )
        return result.scalar_one_or_none()

    async def get_active_goal(self) -> Optional[Goal]:
        """Get the currently active goal."""
        result = await self.session.execute(
            select(Goal)
            .options(selectinload(Goal.actions))
            .where(Goal.status == GoalStatus.ACTIVE)
            .order_by(Goal.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_pending_goals(self) -> List[Goal]:
        """Get all pending goals in order of creation."""
        result = await self.session.execute(
            select(Goal)
            .where(Goal.status == GoalStatus.PENDING)
            .order_by(Goal.created_at.asc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        description: str,
        source: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Goal:
        """Create a new goal."""
        goal = Goal(
            id=str(uuid4()),
            description=description,
            status=GoalStatus.PENDING,
            source=source,
            source_id=source_id,
        )
        self.session.add(goal)
        await self.session.flush()
        await self.session.refresh(goal)
        return goal

    async def update_status(
        self,
        goal_id: str,
        status: GoalStatus,
        error: Optional[str] = None,
    ) -> Optional[Goal]:
        """Update goal status."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.status = status

        if status == GoalStatus.ACTIVE and not goal.started_at:
            goal.started_at = datetime.utcnow()
        elif status in [GoalStatus.COMPLETED, GoalStatus.FAILED]:
            goal.completed_at = datetime.utcnow()

        if error:
            goal.error = error

        await self.session.flush()
        await self.session.refresh(goal)
        return goal

    async def update_cards(self, goal_id: str, card_ids: List[str]) -> Optional[Goal]:
        """Update the list of cards for a goal."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.cards = card_ids
        await self.session.flush()
        await self.session.refresh(goal)
        return goal

    async def add_card(self, goal_id: str, card_id: str) -> Optional[Goal]:
        """Add a card to a goal's card list."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        cards = goal.cards or []
        if card_id not in cards:
            cards.append(card_id)
            goal.cards = cards

        await self.session.flush()
        await self.session.refresh(goal)
        return goal

    async def set_learning(
        self,
        goal_id: str,
        learning: str,
        learning_id: Optional[str] = None,
    ) -> Optional[Goal]:
        """Set the learning for a completed goal."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.learning = learning
        if learning_id:
            goal.learning_id = learning_id

        await self.session.flush()
        await self.session.refresh(goal)
        return goal

    async def update_metrics(
        self,
        goal_id: str,
        tokens: int,
        cost_usd: float,
    ) -> Optional[Goal]:
        """Add to goal metrics."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return None

        goal.total_tokens += tokens
        goal.total_cost_usd += cost_usd

        await self.session.flush()
        await self.session.refresh(goal)
        return goal

    async def delete(self, goal_id: str) -> bool:
        """Delete a goal and its actions."""
        goal = await self.get_by_id(goal_id)
        if not goal:
            return False

        await self.session.delete(goal)
        await self.session.flush()
        return True


class ActionRepository:
    """Repository for OrchestratorAction database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, action_id: str) -> Optional[OrchestratorAction]:
        """Get an action by ID."""
        result = await self.session.execute(
            select(OrchestratorAction).where(OrchestratorAction.id == action_id)
        )
        return result.scalar_one_or_none()

    async def get_by_goal(self, goal_id: str) -> List[OrchestratorAction]:
        """Get all actions for a goal."""
        result = await self.session.execute(
            select(OrchestratorAction)
            .where(OrchestratorAction.goal_id == goal_id)
            .order_by(OrchestratorAction.started_at.asc())
        )
        return list(result.scalars().all())

    async def get_last_action(self, goal_id: str) -> Optional[OrchestratorAction]:
        """Get the most recent action for a goal."""
        result = await self.session.execute(
            select(OrchestratorAction)
            .where(OrchestratorAction.goal_id == goal_id)
            .order_by(OrchestratorAction.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        goal_id: str,
        action_type: ActionType,
        input_context: Optional[dict] = None,
        card_id: Optional[str] = None,
    ) -> OrchestratorAction:
        """Create a new action."""
        action = OrchestratorAction(
            id=str(uuid4()),
            goal_id=goal_id,
            action_type=action_type,
            input_context=input_context,
            card_id=card_id,
        )
        self.session.add(action)
        await self.session.flush()
        await self.session.refresh(action)
        return action

    async def complete(
        self,
        action_id: str,
        success: bool,
        output_result: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> Optional[OrchestratorAction]:
        """Mark an action as completed."""
        action = await self.get_by_id(action_id)
        if not action:
            return None

        action.completed_at = datetime.utcnow()
        action.success = success
        action.output_result = output_result
        action.error = error

        await self.session.flush()
        await self.session.refresh(action)
        return action


class LogRepository:
    """Repository for OrchestratorLog database operations."""

    def __init__(self, session: AsyncSession, retention_hours: int = 24):
        self.session = session
        self.retention_hours = retention_hours

    async def add(
        self,
        log_type: OrchestratorLogType,
        content: str,
        context: Optional[dict] = None,
        goal_id: Optional[str] = None,
    ) -> OrchestratorLog:
        """Add a new log entry."""
        log = OrchestratorLog(
            id=str(uuid4()),
            log_type=log_type,
            content=content,
            context=context,
            goal_id=goal_id,
            expires_at=datetime.utcnow() + timedelta(hours=self.retention_hours),
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def get_recent(
        self,
        limit: int = 50,
        log_types: Optional[List[OrchestratorLogType]] = None,
        goal_id: Optional[str] = None,
    ) -> List[OrchestratorLog]:
        """Get recent logs."""
        query = select(OrchestratorLog).order_by(OrchestratorLog.timestamp.desc())

        if log_types:
            query = query.where(OrchestratorLog.log_type.in_(log_types))

        if goal_id:
            query = query.where(OrchestratorLog.goal_id == goal_id)

        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_context_summary(self, limit: int = 10) -> List[dict]:
        """Get a summary of recent logs for context."""
        logs = await self.get_recent(limit=limit)
        return [
            {
                "type": log.log_type.value,
                "content": log.content,
                "timestamp": log.timestamp.isoformat(),
                "goal_id": log.goal_id,
            }
            for log in logs
        ]

    async def cleanup_expired(self) -> int:
        """Remove expired log entries."""
        result = await self.session.execute(
            delete(OrchestratorLog)
            .where(OrchestratorLog.expires_at < datetime.utcnow())
        )
        await self.session.flush()
        return result.rowcount

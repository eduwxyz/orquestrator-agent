"""Memory service combining short-term (SQLite) and long-term (Qdrant) memory."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.orchestrator_repository import LogRepository, GoalRepository
from ..models.orchestrator import OrchestratorLogType
from .qdrant_service import get_qdrant_service

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Unified memory service for the orchestrator.

    Short-term memory (SQLite):
    - Recent logs and context
    - Current execution state
    - Recent goals and actions

    Long-term memory (Qdrant):
    - Learnings from completed goals
    - Patterns and insights
    - Searchable via semantic similarity
    """

    def __init__(self, session: AsyncSession, retention_hours: int = 24):
        self.session = session
        self.log_repo = LogRepository(session, retention_hours)
        self.goal_repo = GoalRepository(session)
        self.qdrant = get_qdrant_service()

    # ==================== SHORT-TERM MEMORY (SQLite) ====================

    async def record_step(
        self,
        step_type: OrchestratorLogType,
        content: str,
        context: Optional[dict] = None,
        goal_id: Optional[str] = None,
    ) -> None:
        """Record an orchestrator step in short-term memory."""
        await self.log_repo.add(
            log_type=step_type,
            content=content,
            context=context,
            goal_id=goal_id,
        )
        logger.debug(f"[Memory] Recorded {step_type.value}: {content[:50]}...")

    async def get_recent_context(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get recent context from short-term memory.

        Returns:
            Dictionary with:
            - recent_logs: List of recent log entries
            - active_goal: Currently active goal if any
            - pending_goals: Goals waiting to be processed
        """
        # Get recent logs
        recent_logs = await self.log_repo.get_context_summary(limit=limit)

        # Get active goal
        active_goal = await self.goal_repo.get_active_goal()
        active_goal_data = None
        if active_goal:
            active_goal_data = {
                "id": active_goal.id,
                "description": active_goal.description,
                "status": active_goal.status.value,
                "cards": active_goal.cards or [],
                "started_at": active_goal.started_at.isoformat() if active_goal.started_at else None,
            }

        # Get pending goals count
        pending_goals = await self.goal_repo.get_pending_goals()

        return {
            "recent_logs": recent_logs,
            "active_goal": active_goal_data,
            "pending_goals_count": len(pending_goals),
            "has_pending_goals": len(pending_goals) > 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def cleanup_expired_logs(self) -> int:
        """Clean up expired short-term memory logs."""
        count = await self.log_repo.cleanup_expired()
        if count > 0:
            logger.info(f"[Memory] Cleaned up {count} expired logs")
        return count

    # ==================== LONG-TERM MEMORY (Qdrant) ====================

    def store_learning(
        self,
        goal_description: str,
        learning: str,
        cards_created: List[str],
        outcome: str,
        error_encountered: Optional[str] = None,
        fix_applied: Optional[str] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> Optional[str]:
        """
        Store a learning in long-term memory (Qdrant).

        Returns:
            Learning ID if successful, None otherwise
        """
        try:
            learning_id = self.qdrant.store_learning(
                goal_description=goal_description,
                learning=learning,
                cards_created=cards_created,
                outcome=outcome,
                error_encountered=error_encountered,
                fix_applied=fix_applied,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
            )
            logger.info(f"[Memory] Stored learning {learning_id}")
            return learning_id
        except Exception as e:
            logger.error(f"[Memory] Failed to store learning: {e}")
            return None

    def query_relevant_learnings(
        self,
        context: str,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Query relevant learnings from long-term memory.

        Args:
            context: Current context to find relevant learnings for
            limit: Maximum number of learnings to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of relevant learnings with their scores
        """
        try:
            learnings = self.qdrant.query_learnings(
                query_text=context,
                limit=limit,
                score_threshold=min_score,
            )
            logger.info(f"[Memory] Found {len(learnings)} relevant learnings")
            return learnings
        except Exception as e:
            logger.error(f"[Memory] Failed to query learnings: {e}")
            return []

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about long-term memory."""
        try:
            return self.qdrant.get_collection_stats()
        except Exception as e:
            logger.error(f"[Memory] Failed to get stats: {e}")
            return {"error": str(e)}

    # ==================== COMBINED MEMORY OPERATIONS ====================

    async def get_full_context(self, goal_description: Optional[str] = None) -> Dict[str, Any]:
        """
        Get full context combining short-term and long-term memory.

        Args:
            goal_description: If provided, also queries relevant learnings

        Returns:
            Combined context from both memory systems
        """
        # Get short-term context
        short_term = await self.get_recent_context()

        # Query long-term learnings if we have context
        long_term_learnings = []
        if goal_description:
            long_term_learnings = self.query_relevant_learnings(
                context=goal_description,
                limit=3,
            )

        return {
            "short_term": short_term,
            "long_term_learnings": long_term_learnings,
            "has_learnings": len(long_term_learnings) > 0,
        }

    def health_check(self) -> Dict[str, bool]:
        """Check health of both memory systems."""
        qdrant_healthy = self.qdrant.health_check()

        return {
            "short_term": True,  # SQLite is always available if we got here
            "long_term": qdrant_healthy,
        }

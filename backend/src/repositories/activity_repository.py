"""Activity repository for database operations."""

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.activity_log import ActivityLog, ActivityType
from ..models.card import Card


class ActivityRepository:
    """Repository for ActivityLog database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_activity(
        self,
        card_id: str,
        activity_type: ActivityType,
        from_column: Optional[str] = None,
        to_column: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ActivityLog:
        """
        Log a new activity for a card.

        Args:
            card_id: ID of the card
            activity_type: Type of activity
            from_column: Previous column (for moves)
            to_column: Target column (for moves)
            old_value: Previous value (for updates)
            new_value: New value (for updates)
            user_id: ID of user who performed the action
            description: Additional description

        Returns:
            Created ActivityLog instance
        """
        activity = ActivityLog(
            id=str(uuid4()),
            card_id=card_id,
            activity_type=activity_type,
            timestamp=datetime.utcnow(),
            from_column=from_column,
            to_column=to_column,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            description=description,
        )

        self.session.add(activity)
        await self.session.flush()
        await self.session.refresh(activity)
        return activity

    async def get_recent_activities(
        self, limit: int = 10, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get recent activities with card information.

        Args:
            limit: Maximum number of activities to return
            offset: Number of activities to skip

        Returns:
            List of activity dictionaries with card info
        """
        query = (
            select(ActivityLog, Card.title, Card.description)
            .join(Card, ActivityLog.card_id == Card.id)
            .where(Card.archived == False)  # Only show activities from non-archived cards
            .order_by(desc(ActivityLog.timestamp))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(query)
        activities = []

        for activity, card_title, card_description in result:
            activities.append({
                "id": activity.id,
                "cardId": activity.card_id,
                "cardTitle": card_title,
                "cardDescription": card_description,
                "type": activity.activity_type.value,
                "timestamp": activity.timestamp.isoformat(),
                "fromColumn": activity.from_column,
                "toColumn": activity.to_column,
                "oldValue": activity.old_value,
                "newValue": activity.new_value,
                "userId": activity.user_id,
                "description": activity.description,
            })

        return activities

    async def get_card_activities(self, card_id: str) -> list[dict[str, Any]]:
        """
        Get all activities for a specific card.

        Args:
            card_id: ID of the card

        Returns:
            List of activity dictionaries
        """
        query = (
            select(ActivityLog)
            .where(ActivityLog.card_id == card_id)
            .order_by(desc(ActivityLog.timestamp))
        )

        result = await self.session.execute(query)
        activities = []

        for activity in result.scalars():
            activities.append({
                "id": activity.id,
                "cardId": activity.card_id,
                "type": activity.activity_type.value,
                "timestamp": activity.timestamp.isoformat(),
                "fromColumn": activity.from_column,
                "toColumn": activity.to_column,
                "oldValue": activity.old_value,
                "newValue": activity.new_value,
                "userId": activity.user_id,
                "description": activity.description,
            })

        return activities

    async def delete_old_activities(self, days: int = 90) -> int:
        """
        Delete activities older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted activities
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = select(ActivityLog).where(ActivityLog.timestamp < cutoff_date)
        result = await self.session.execute(query)
        activities = result.scalars().all()

        count = len(activities)
        for activity in activities:
            await self.session.delete(activity)

        await self.session.flush()
        return count

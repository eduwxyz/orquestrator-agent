"""Activity routes for the API."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..repositories.activity_repository import ActivityRepository

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("/recent")
async def get_recent_activities(
    limit: int = Query(default=10, le=50, description="Maximum number of activities to return"),
    offset: int = Query(default=0, ge=0, description="Number of activities to skip"),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Get recent activities ordered by timestamp.

    Args:
        limit: Maximum number of activities (max 50)
        offset: Number of activities to skip for pagination
        session: Database session

    Returns:
        List of activity dictionaries with card information
    """
    repo = ActivityRepository(session)
    activities = await repo.get_recent_activities(limit=limit, offset=offset)
    return activities


@router.get("/card/{card_id}")
async def get_card_activities(
    card_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Get activity history for a specific card.

    Args:
        card_id: ID of the card
        session: Database session

    Returns:
        List of activity dictionaries for the card
    """
    repo = ActivityRepository(session)
    activities = await repo.get_card_activities(card_id)
    return activities

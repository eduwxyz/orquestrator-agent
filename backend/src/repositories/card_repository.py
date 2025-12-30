"""Card repository for database operations."""

from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.card import Card
from ..schemas.card import CardCreate, CardUpdate, ColumnId


# Transições permitidas no SDLC
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "backlog": ["plan", "cancelado"],
    "plan": ["in-progress", "cancelado"],
    "in-progress": ["test", "cancelado"],
    "test": ["review", "cancelado"],
    "review": ["done", "cancelado"],
    "done": ["archived", "cancelado"],
    "archived": ["done"],
    "cancelado": [],  # Não permite sair de cancelado
}


class CardRepository:
    """Repository for Card database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self, include_archived: bool = True) -> list[Card]:
        """Get all cards ordered by creation date."""
        query = select(Card).order_by(Card.created_at)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, card_id: str) -> Optional[Card]:
        """Get a card by its ID."""
        result = await self.session.execute(
            select(Card).where(Card.id == card_id)
        )
        return result.scalar_one_or_none()

    async def create(self, card_data: CardCreate) -> Card:
        """Create a new card in the backlog column."""
        card = Card(
            id=str(uuid4()),
            title=card_data.title,
            description=card_data.description,
            column_id="backlog",
        )
        self.session.add(card)
        await self.session.flush()
        await self.session.refresh(card)
        return card

    async def update(self, card_id: str, card_data: CardUpdate) -> Optional[Card]:
        """Update an existing card."""
        card = await self.get_by_id(card_id)
        if not card:
            return None

        update_data = card_data.model_dump(exclude_unset=True, by_alias=False)
        for field, value in update_data.items():
            if value is not None:
                setattr(card, field, value)

        await self.session.flush()
        await self.session.refresh(card)
        return card

    async def delete(self, card_id: str) -> bool:
        """Delete a card by its ID."""
        card = await self.get_by_id(card_id)
        if not card:
            return False

        await self.session.delete(card)
        await self.session.flush()
        return True

    async def move(self, card_id: str, new_column_id: ColumnId) -> tuple[Optional[Card], Optional[str]]:
        """
        Move a card to a new column with SDLC validation.

        Returns:
            tuple: (card, error_message) - card if successful, error_message if failed
        """
        card = await self.get_by_id(card_id)
        if not card:
            return None, "Card not found"

        current_column = card.column_id
        allowed = ALLOWED_TRANSITIONS.get(current_column, [])

        if new_column_id not in allowed:
            return None, f"Invalid transition from '{current_column}' to '{new_column_id}'. Allowed: {allowed}"

        card.column_id = new_column_id
        await self.session.flush()
        await self.session.refresh(card)
        return card, None

    async def update_spec_path(self, card_id: str, spec_path: str) -> Optional[Card]:
        """Update the spec_path for a card."""
        card = await self.get_by_id(card_id)
        if not card:
            return None

        card.spec_path = spec_path
        await self.session.flush()
        await self.session.refresh(card)
        return card


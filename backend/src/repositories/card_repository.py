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
    "plan": ["implement", "cancelado"],
    "implement": ["test", "cancelado"],
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
            model_plan=card_data.model_plan,
            model_implement=card_data.model_implement,
            model_test=card_data.model_test,
            model_review=card_data.model_review,
            parent_card_id=getattr(card_data, 'parent_card_id', None),
            is_fix_card=getattr(card_data, 'is_fix_card', False),
            test_error_context=getattr(card_data, 'test_error_context', None),
            base_branch=getattr(card_data, 'base_branch', None),
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
        Move a card to a new column with SDLC and finalization validation.

        Returns:
            tuple: (card, error_message) - card if successful, error_message if failed
        """
        card = await self.get_by_id(card_id)
        if not card:
            return None, "Card not found"

        current_column = card.column_id

        # Verificar se o card está finalizado
        finalized_columns = ['done', 'archived', 'cancelado']
        if current_column not in finalized_columns and current_column != new_column_id:
            # Card não finalizado - apenas permitir transições SDLC válidas
            allowed = ALLOWED_TRANSITIONS.get(current_column, [])
            if new_column_id not in allowed:
                return None, f"Card precisa ser finalizado antes de poder ser movido. Finalize movendo para Done, Archived ou Cancelado."

        # Validação SDLC existente
        allowed = ALLOWED_TRANSITIONS.get(current_column, [])
        if new_column_id not in allowed and current_column != new_column_id:
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

    async def get_active_fix_card(self, parent_card_id: str) -> Optional[Card]:
        """Get an active (non-archived, non-cancelled) fix card for a parent card."""
        result = await self.session.execute(
            select(Card).where(
                Card.parent_card_id == parent_card_id,
                Card.is_fix_card == True,
                Card.column_id.notin_(["done", "archived", "cancelado"])
            )
        )
        return result.scalar_one_or_none()

    async def create_fix_card(self, parent_card_id: str, error_info: dict) -> Optional[Card]:
        """Create a fix card for a parent card with test failure."""
        # Check if there's already an active fix card
        existing_fix = await self.get_active_fix_card(parent_card_id)
        if existing_fix:
            return existing_fix

        # Get parent card to copy configuration
        parent_card = await self.get_by_id(parent_card_id)
        if not parent_card:
            return None

        # Create the fix card
        fix_card_data = CardCreate(
            title=f"[FIX] {parent_card.title[:50]}",
            description=error_info.get("description", ""),
            model_plan=parent_card.model_plan,
            model_implement=parent_card.model_implement,
            model_test=parent_card.model_test,
            model_review=parent_card.model_review,
            parent_card_id=parent_card_id,
            is_fix_card=True,
            test_error_context=error_info.get("context", "")
        )

        return await self.create(fix_card_data)


"""Card routes for the API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..repositories.card_repository import CardRepository
from ..schemas.card import (
    CardCreate,
    CardUpdate,
    CardMove,
    CardResponse,
    CardsListResponse,
    CardSingleResponse,
    CardDeleteResponse,
)

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("", response_model=CardsListResponse)
async def get_all_cards(db: AsyncSession = Depends(get_db)):
    """Get all cards."""
    repo = CardRepository(db)
    cards = await repo.get_all()
    return CardsListResponse(
        cards=[CardResponse.model_validate(card) for card in cards]
    )


@router.get("/{card_id}", response_model=CardSingleResponse)
async def get_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single card by ID."""
    repo = CardRepository(db)
    card = await repo.get_by_id(card_id)

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    return CardSingleResponse(card=CardResponse.model_validate(card))


@router.post("", response_model=CardSingleResponse, status_code=201)
async def create_card(card_data: CardCreate, db: AsyncSession = Depends(get_db)):
    """Create a new card in the backlog column."""
    repo = CardRepository(db)
    card = await repo.create(card_data)
    return CardSingleResponse(card=CardResponse.model_validate(card))


@router.put("/{card_id}", response_model=CardSingleResponse)
async def update_card(
    card_id: str, card_data: CardUpdate, db: AsyncSession = Depends(get_db)
):
    """Update an existing card."""
    repo = CardRepository(db)
    card = await repo.update(card_id, card_data)

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    return CardSingleResponse(card=CardResponse.model_validate(card))


@router.delete("/{card_id}", response_model=CardDeleteResponse)
async def delete_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a card."""
    repo = CardRepository(db)
    deleted = await repo.delete(card_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Card not found")

    return CardDeleteResponse()


@router.patch("/{card_id}/move", response_model=CardSingleResponse)
async def move_card(
    card_id: str, move_data: CardMove, db: AsyncSession = Depends(get_db)
):
    """Move a card to another column with SDLC validation."""
    repo = CardRepository(db)
    card, error = await repo.move(card_id, move_data.column_id)

    if error:
        raise HTTPException(status_code=400, detail=error)

    return CardSingleResponse(card=CardResponse.model_validate(card))


@router.patch("/{card_id}/spec-path", response_model=CardSingleResponse)
async def update_spec_path(
    card_id: str, spec_path: str, db: AsyncSession = Depends(get_db)
):
    """Update the spec path for a card."""
    repo = CardRepository(db)
    card = await repo.update_spec_path(card_id, spec_path)

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    return CardSingleResponse(card=CardResponse.model_validate(card))



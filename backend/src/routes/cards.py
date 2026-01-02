"""Card routes for the API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
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
    ActiveExecution,
)

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("", response_model=CardsListResponse)
async def get_all_cards(db: AsyncSession = Depends(get_db)):
    """Get all cards with active executions."""
    repo = CardRepository(db)
    cards = await repo.get_all()

    # Para cada card, buscar execução ativa se houver
    cards_with_execution = []
    for card in cards:
        card_dict = card.__dict__.copy()

        # Buscar execução ativa no banco (usar SQL direto por enquanto)
        result = await db.execute(
            select(1).select_from(text("executions"))
            .where(text("card_id = :card_id AND is_active = 1"))
            .params(card_id=card.id)
        )
        execution = result.first()

        if execution:
            # Buscar detalhes da execução
            exec_result = await db.execute(
                text("""
                    SELECT id, status, command, started_at, completed_at
                    FROM executions
                    WHERE card_id = :card_id AND is_active = 1
                """).params(card_id=card.id)
            )
            exec_data = exec_result.first()

            if exec_data:
                # started_at e completed_at podem vir como string ou datetime do SQLite
                started_at = exec_data[3]
                completed_at = exec_data[4]

                card_dict["activeExecution"] = ActiveExecution(
                    id=exec_data[0],
                    status=exec_data[1],
                    command=exec_data[2],
                    startedAt=started_at if isinstance(started_at, str) else (started_at.isoformat() if started_at else None),
                    completedAt=completed_at if isinstance(completed_at, str) else (completed_at.isoformat() if completed_at else None)
                )

        cards_with_execution.append(CardResponse.model_validate(card_dict))

    return CardsListResponse(cards=cards_with_execution)


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



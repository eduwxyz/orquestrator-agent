"""Card routes for the API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..repositories.card_repository import CardRepository
from ..repositories.execution_repository import ExecutionRepository
from ..schemas.card import (
    CardCreate,
    CardUpdate,
    CardMove,
    CardResponse,
    CardsListResponse,
    CardSingleResponse,
    CardDeleteResponse,
    ActiveExecution,
    DiffStats,
    TokenStats,
    CostStats,
)
from ..services.diff_analyzer import DiffAnalyzer
from ..models.card import Card

router = APIRouter(prefix="/api/cards", tags=["cards"])


def card_to_dict(card: Card) -> dict:
    """Convert Card model to dict, avoiding SQLAlchemy internal state."""
    return {
        "id": card.id,
        "title": card.title,
        "description": card.description,
        "column_id": card.column_id,
        "spec_path": card.spec_path,
        "model_plan": card.model_plan,
        "model_implement": card.model_implement,
        "model_test": card.model_test,
        "model_review": card.model_review,
        "images": card.images,
        "archived": card.archived,
        "created_at": card.created_at,
        "updated_at": card.updated_at,
        "parent_card_id": card.parent_card_id,
        "is_fix_card": card.is_fix_card,
        "test_error_context": card.test_error_context,
        "branch_name": card.branch_name,
        "worktree_path": card.worktree_path,
        "base_branch": card.base_branch,
        "diff_stats": card.diff_stats,
        "completed_at": card.completed_at,
        "experts": card.experts,
        "dependencies": card.dependencies,
    }


@router.get("", response_model=CardsListResponse)
async def get_all_cards(db: AsyncSession = Depends(get_db)):
    """Get all cards with active executions and token stats."""
    repo = CardRepository(db)
    exec_repo = ExecutionRepository(db)
    cards = await repo.get_all()

    # Para cada card, buscar execução ativa e token stats
    cards_with_execution = []
    for card in cards:
        card_dict = card_to_dict(card)

        # Buscar execução ativa no banco (usar SQL direto por enquanto)
        result = await db.execute(
            select(1).select_from(text("executions"))
            .where(text("card_id = :card_id AND is_active = 1"))
            .params(card_id=card.id)
        )
        execution = result.first()

        if execution:
            # Buscar detalhes da execução incluindo workflow state
            exec_result = await db.execute(
                text("""
                    SELECT id, status, command, started_at, completed_at, workflow_stage, workflow_error
                    FROM executions
                    WHERE card_id = :card_id AND is_active = 1
                """).params(card_id=card.id)
            )
            exec_data = exec_result.first()

            if exec_data:
                # started_at e completed_at podem vir como string ou datetime do SQLite
                started_at = exec_data[3]
                completed_at = exec_data[4]
                workflow_stage = exec_data[5]
                workflow_error = exec_data[6]

                card_dict["activeExecution"] = ActiveExecution(
                    id=exec_data[0],
                    status=exec_data[1],
                    command=exec_data[2],
                    startedAt=started_at if isinstance(started_at, str) else (started_at.isoformat() if started_at else None),
                    completedAt=completed_at if isinstance(completed_at, str) else (completed_at.isoformat() if completed_at else None),
                    workflowStage=workflow_stage,
                    workflowError=workflow_error
                )

        # Buscar token stats para o card
        token_stats = await exec_repo.get_token_stats_for_card(card.id)
        if token_stats.get("totalTokens", 0) > 0:
            card_dict["tokenStats"] = TokenStats(**token_stats)

        # Buscar cost stats para o card
        cost_stats = await exec_repo.get_cost_stats_for_card(card.id)
        if cost_stats.get("totalCost", 0.0) > 0:
            card_dict["costStats"] = CostStats(**cost_stats)

        cards_with_execution.append(CardResponse.model_validate(card_dict))

    return CardsListResponse(cards=cards_with_execution)


@router.get("/{card_id}", response_model=CardSingleResponse)
async def get_card(card_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single card by ID."""
    repo = CardRepository(db)
    exec_repo = ExecutionRepository(db)
    card = await repo.get_by_id(card_id)

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    card_dict = card_to_dict(card)

    # Buscar token stats para o card
    token_stats = await exec_repo.get_token_stats_for_card(card.id)
    if token_stats.get("totalTokens", 0) > 0:
        card_dict["tokenStats"] = TokenStats(**token_stats)

    # Buscar cost stats para o card
    cost_stats = await exec_repo.get_cost_stats_for_card(card.id)
    if cost_stats.get("totalCost", 0.0) > 0:
        card_dict["costStats"] = CostStats(**cost_stats)

    return CardSingleResponse(card=CardResponse.model_validate(card_dict))


@router.post("", response_model=CardSingleResponse, status_code=201)
async def create_card(card_data: CardCreate, db: AsyncSession = Depends(get_db)):
    """Create a new card in the backlog column."""
    repo = CardRepository(db)
    card = await repo.create(card_data)

    # Broadcast the new card via WebSocket
    from ..services.card_ws import card_ws_manager
    card_response = CardResponse.model_validate(card)
    card_dict = card_response.model_dump(by_alias=True, mode='json')
    await card_ws_manager.broadcast_card_created(
        card_id=card.id,
        card_data=card_dict
    )

    return CardSingleResponse(card=card_response)


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

    # Get current card state before move
    current_card = await repo.get_by_id(card_id)
    if not current_card:
        raise HTTPException(status_code=404, detail="Card not found")

    from_column = current_card.column_id

    # Perform the move
    card, error = await repo.move(card_id, move_data.column_id)

    if error:
        raise HTTPException(status_code=400, detail=error)

    # Auto-capture diff when moving to review or done
    if move_data.column_id in ["review", "done"]:
        if card.worktree_path and card.branch_name:
            try:
                diff_analyzer = DiffAnalyzer()
                diff_stats = await diff_analyzer.capture_diff(
                    card.worktree_path,
                    card.branch_name
                )
                if diff_stats:
                    card_update = CardUpdate(diff_stats=diff_stats)
                    card = await repo.update(card_id, card_update)
            except Exception as e:
                # Log error but don't fail the move
                print(f"Failed to capture diff for card {card_id}: {e}")

    # Broadcast the change via WebSocket
    from ..services.card_ws import card_ws_manager
    card_response = CardResponse.model_validate(card)
    card_dict = card_response.model_dump(by_alias=True, mode='json')
    await card_ws_manager.broadcast_card_moved(
        card_id=card_id,
        from_column=from_column,
        to_column=move_data.column_id,
        card_data=card_dict
    )

    return CardSingleResponse(card=card_response)


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


@router.post("/{card_id}/capture-diff", response_model=CardSingleResponse)
async def capture_diff(card_id: str, db: AsyncSession = Depends(get_db)):
    """Capture diff statistics for a card when it moves to review/done."""
    repo = CardRepository(db)
    card = await repo.get_by_id(card_id)

    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Only capture diff for cards in review or done
    if card.column_id not in ["review", "done"]:
        raise HTTPException(
            status_code=400,
            detail="Can only capture diff for cards in review or done columns"
        )

    # Check if card has worktree info
    if not card.worktree_path or not card.branch_name:
        raise HTTPException(
            status_code=400,
            detail="Card must have worktree information to capture diff"
        )

    # Capture diff
    diff_analyzer = DiffAnalyzer()
    diff_stats = await diff_analyzer.capture_diff(
        card.worktree_path,
        card.branch_name
    )

    if not diff_stats:
        raise HTTPException(
            status_code=500,
            detail="Failed to capture diff statistics"
        )

    # Update card with diff stats
    card_update = CardUpdate(diff_stats=diff_stats)
    card = await repo.update(card_id, card_update)

    return CardSingleResponse(card=CardResponse.model_validate(card))



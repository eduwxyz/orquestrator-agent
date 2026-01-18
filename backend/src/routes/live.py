"""Live spectator routes and WebSocket."""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.card import Card
from ..models.live import Vote, VoteType, CompletedProject
from ..schemas.live import (
    LiveStatusResponse, LiveKanbanResponse, LiveCardResponse,
    VotingStateResponse, VoteRequest, VoteResponse,
    ProjectGalleryResponse, CompletedProjectSchema,
    LikeRequest, LikeResponse
)
from ..services.presence_service import get_presence_service
from ..services.voting_service import get_voting_service
from ..services.live_broadcast_service import get_live_broadcast_service

router = APIRouter(prefix="/api/live", tags=["live"])


# ============================================================================
# REST Endpoints
# ============================================================================

@router.get("/status", response_model=LiveStatusResponse)
async def get_live_status():
    """Get current AI status for spectators."""
    broadcast = get_live_broadcast_service()
    presence = get_presence_service()

    status = broadcast._current_status
    return LiveStatusResponse(
        is_working=status.get("is_working", False),
        current_stage=status.get("current_stage"),
        current_card=status.get("current_card"),
        progress=status.get("progress"),
        spectator_count=presence.count
    )


@router.get("/kanban", response_model=LiveKanbanResponse)
async def get_live_kanban(db: AsyncSession = Depends(get_db)):
    """Get Kanban board state for spectators (read-only)."""
    # Get all non-archived cards
    result = await db.execute(
        select(Card)
        .where(Card.archived == False)
        .order_by(Card.created_at.desc())
    )
    cards = result.scalars().all()

    # Group by column
    columns = {
        "backlog": [],
        "planning": [],
        "implementing": [],
        "testing": [],
        "review": [],
        "done": []
    }

    for card in cards:
        col = card.column_id
        if col in columns:
            columns[col].append(LiveCardResponse(
                id=card.id,
                title=card.title,
                description=card.description,
                column_id=card.column_id,
                created_at=card.created_at
            ))

    return LiveKanbanResponse(
        columns=columns,
        total_cards=len(cards)
    )


@router.get("/voting", response_model=VotingStateResponse)
async def get_voting_state():
    """Get current voting state."""
    voting = get_voting_service()
    return voting.get_state()


@router.post("/vote", response_model=VoteResponse)
async def cast_vote(
    request: VoteRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """Cast a vote for the next project."""
    voting = get_voting_service()

    # Get IP address for rate limiting
    ip = req.client.host if req.client else None

    success, message, new_count = await voting.vote(
        db=db,
        option_id=request.option_id,
        session_id=request.session_id,
        ip_address=ip
    )

    return VoteResponse(
        success=success,
        message=message,
        new_vote_count=new_count
    )


@router.get("/projects", response_model=ProjectGalleryResponse)
async def get_completed_projects(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get completed projects gallery."""
    # Get completed projects ordered by likes
    result = await db.execute(
        select(CompletedProject)
        .order_by(CompletedProject.like_count.desc(), CompletedProject.completed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    projects = result.scalars().all()

    # Get total count
    count_result = await db.execute(select(func.count(CompletedProject.id)))
    total = count_result.scalar() or 0

    return ProjectGalleryResponse(
        projects=[
            CompletedProjectSchema(
                id=p.id,
                title=p.title,
                description=p.description,
                category=p.category,
                screenshot_url=p.screenshot_url,
                preview_url=p.preview_url,
                like_count=p.like_count,
                completed_at=p.completed_at
            )
            for p in projects
        ],
        total=total
    )


@router.post("/projects/{project_id}/like", response_model=LikeResponse)
async def like_project(
    project_id: str,
    request: LikeRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """Like a completed project."""
    # Check if project exists
    result = await db.execute(
        select(CompletedProject).where(CompletedProject.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if already liked by this session
    ip = req.client.host if req.client else None
    like_result = await db.execute(
        select(Vote)
        .where(
            Vote.vote_type == VoteType.LIKE,
            Vote.target_id == project_id,
            Vote.session_id == request.session_id
        )
    )
    existing_like = like_result.scalar_one_or_none()

    if existing_like:
        return LikeResponse(
            success=False,
            message="You have already liked this project",
            new_like_count=project.like_count
        )

    # Create like vote
    like_vote = Vote(
        vote_type=VoteType.LIKE,
        target_id=project_id,
        session_id=request.session_id,
        ip_address=ip
    )
    db.add(like_vote)

    # Update like count
    project.like_count += 1
    await db.execute(
        update(CompletedProject)
        .where(CompletedProject.id == project_id)
        .values(like_count=project.like_count)
    )

    await db.commit()

    # Broadcast like
    broadcast = get_live_broadcast_service()
    await broadcast.broadcast_project_liked(project_id, project.like_count)

    return LikeResponse(
        success=True,
        message="Like recorded",
        new_like_count=project.like_count
    )


# ============================================================================
# Admin Endpoints (for starting voting, adding projects)
# ============================================================================

@router.post("/admin/start-voting")
async def admin_start_voting(
    duration_seconds: int = 300,
    db: AsyncSession = Depends(get_db)
):
    """Start a new voting round (admin only)."""
    voting = get_voting_service()

    if voting.is_active:
        raise HTTPException(status_code=400, detail="Voting is already active")

    round, options = await voting.start_round(db, duration_seconds)

    return {
        "success": True,
        "round_id": round.id,
        "ends_at": round.ends_at.isoformat(),
        "options": [
            {"id": o.id, "title": o.title, "category": o.category}
            for o in options
        ]
    }


@router.post("/admin/end-voting")
async def admin_end_voting(db: AsyncSession = Depends(get_db)):
    """End current voting round early (admin only)."""
    voting = get_voting_service()

    if not voting.is_active:
        raise HTTPException(status_code=400, detail="No active voting round")

    winner = await voting.end_round(db)

    return {
        "success": True,
        "winner": {
            "id": winner.id,
            "title": winner.title,
            "vote_count": winner.vote_count
        } if winner else None
    }


@router.post("/admin/add-project")
async def admin_add_project(
    title: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    card_id: Optional[str] = None,
    screenshot_url: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Add a completed project to the gallery (admin only)."""
    project = CompletedProject(
        id=str(uuid4()),
        title=title,
        description=description,
        category=category,
        card_id=card_id,
        screenshot_url=screenshot_url,
        like_count=0,
        completed_at=datetime.utcnow()
    )

    db.add(project)
    await db.commit()

    return {
        "success": True,
        "project_id": project.id
    }


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws")
async def live_websocket(websocket: WebSocket):
    """WebSocket endpoint for live spectators."""
    await websocket.accept()

    # Generate session ID
    session_id = str(uuid4())

    # Get broadcast service
    broadcast = get_live_broadcast_service()

    try:
        # Register connection
        await broadcast.connect(session_id, websocket)

        # Handle messages
        while True:
            try:
                data = await websocket.receive_json()

                # Handle ping
                if data.get("type") == "ping":
                    await broadcast.handle_ping(session_id)

            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"[LiveWS] Error handling message: {e}")
                break

    finally:
        # Cleanup
        await broadcast.disconnect(session_id)

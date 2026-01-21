"""Live spectator routes and WebSocket."""

import asyncio
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

from ..database import get_db
from ..models.card import Card
from ..models.orchestrator import Goal, GoalStatus
from ..models.live import Vote, VoteType, CompletedProject, GameScore
from ..schemas.live import (
    LiveStatusResponse, LiveKanbanResponse, LiveCardResponse,
    ProjectGalleryResponse, CompletedProjectSchema,
    LikeRequest, LikeResponse
)
from ..services.presence_service import get_presence_service
from ..services.live_broadcast_service import get_live_broadcast_service

router = APIRouter(prefix="/api/live", tags=["live"])

# ============================================================================
# Live Mode Configuration
# ============================================================================

LIVE_PROJECTS_PATH = os.environ.get("LIVE_PROJECTS_PATH", "/opt/zenflow/live-projects")
LIVE_STARTED_AT_PATH = os.environ.get("LIVE_STARTED_AT_PATH", "/opt/zenflow/backend/live_started_at.txt")

LIVE_MODE_PROMPT = """⚠️ IMPORTANTE: CRIE APENAS 1 CARD. NÃO DECOMPONHA!

Projeto: {project_type}
Pasta do projeto: {project_path}/

## Objetivo da live (entretenimento)
- Precisa ser divertido de assistir ao vivo.
- Tem que ter impacto visual/sonoro imediato.
- Incluir um "wow moment" nos primeiros 2-3 minutos.
- Preferir interatividade (mouse/teclado/gestos) e feedback instantaneo.
- Evitar temas repetidos da live (na duvida, escolha algo diferente).
- Nao repetir projetos registrados em `project_history.txt`.
- Ritmo rapido: algo que mostre progresso visivel em poucos minutos.
- Limite de complexidade: 1 arquivo HTML/CSS/JS inline (sem dependencias externas).

## Estrutura esperada:
- {project_path}/spec.md (plano de implementação)
- {project_path}/index.html (arquivo principal com HTML/CSS/JS inline)

## Instruções:
1. Salve o plano de implementação em `{project_path}/spec.md`
2. Crie o projeto completo em `{project_path}/index.html` com HTML/CSS/JS inline
3. O projeto deve ser funcional, visualmente atraente e divertido

⚠️ REGRA ABSOLUTA: 1 CARD APENAS. Não divida em múltiplas tarefas."""

# Note: Live mode status is now determined by checking if there are cards
# in processing columns (plan, implement, test, review) in the database


# ============================================================================
# REST Endpoints
# ============================================================================

@router.get("/status", response_model=LiveStatusResponse)
async def get_live_status(db: AsyncSession = Depends(get_db)):
    """Get current AI status for spectators."""
    broadcast = get_live_broadcast_service()
    presence = get_presence_service()
    live_started_at = _read_live_started_at()

    # Check if there are cards being processed (source of truth)
    processing_columns = ['plan', 'implement', 'test', 'review']
    result = await db.execute(
        select(func.count(Card.id))
        .where(Card.column_id.in_(processing_columns))
    )
    cards_in_progress = result.scalar() or 0

    # Use broadcast status for details, but override is_working based on DB
    status = broadcast._current_status
    is_working = cards_in_progress > 0 or status.get("is_working", False)

    return LiveStatusResponse(
        is_working=is_working,
        current_stage=status.get("current_stage"),
        current_card=status.get("current_card"),
        progress=status.get("progress"),
        spectator_count=presence.count,
        live_started_at=live_started_at
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

    # Group by column (must match card_repository.py ALLOWED_TRANSITIONS)
    columns = {
        "backlog": [],
        "plan": [],
        "implement": [],
        "test": [],
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
# Game Ranking Endpoints
# ============================================================================

@router.get("/game/ranking")
async def get_game_ranking(
    game_type: str = "snake",
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get game ranking/leaderboard."""
    result = await db.execute(
        select(GameScore)
        .where(GameScore.game_type == game_type)
        .order_by(GameScore.score.desc())
        .limit(limit)
    )
    scores = result.scalars().all()

    return {
        "ranking": [
            {
                "id": s.id,
                "playerName": s.player_name,
                "score": s.score,
                "gameType": s.game_type,
                "createdAt": s.created_at.isoformat()
            }
            for s in scores
        ],
        "total": len(scores)
    }


@router.post("/game/score")
async def submit_game_score(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Submit a game score with retry for concurrent writes."""
    data = await request.json()

    player_name = data.get("player_name", "").strip()[:50]
    score = data.get("score", 0)
    game_type = data.get("game_type", "snake")
    session_id = data.get("session_id", str(uuid4()))

    if not player_name:
        raise HTTPException(status_code=400, detail="Player name is required")

    if score <= 0:
        raise HTTPException(status_code=400, detail="Score must be positive")

    # Retry logic for concurrent writes (SQLite database locked)
    # With WAL mode, locks should be rare, but we still handle them gracefully
    max_retries = 8
    game_score = None

    for attempt in range(max_retries):
        try:
            # Create score entry
            game_score = GameScore(
                id=str(uuid4()),
                player_name=player_name,
                session_id=session_id,
                game_type=game_type,
                score=score
            )

            db.add(game_score)
            await db.commit()
            break  # Success, exit retry loop

        except OperationalError as e:
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                await db.rollback()
                wait_time = 0.5 * (attempt + 1)  # 0.5s, 1s, 1.5s, 2s, 2.5s, 3s, 3.5s
                logger.warning(f"[GameScore] DB locked, retry {attempt + 1}/{max_retries} in {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"[GameScore] Failed to save score after {attempt + 1} attempts: {e}")
                raise HTTPException(status_code=503, detail="Database busy, please try again")

    if not game_score:
        raise HTTPException(status_code=503, detail="Failed to save score")

    # Check rank (read operation, less likely to lock)
    try:
        result = await db.execute(
            select(func.count(GameScore.id))
            .where(GameScore.game_type == game_type)
            .where(GameScore.score > score)
        )
        rank = (result.scalar() or 0) + 1
    except OperationalError:
        rank = 99  # Fallback rank if read fails

    # Broadcast to all viewers if top 10
    if rank <= 10:
        broadcast = get_live_broadcast_service()
        await broadcast.broadcast({
            "type": "game_ranking_update",
            "entry": {
                "id": game_score.id,
                "playerName": player_name,
                "score": score,
                "gameType": game_type,
                "createdAt": game_score.created_at.isoformat(),
                "isNew": True
            },
            "rank": rank
        })

        # Also broadcast as log for visibility
        if rank == 1:
            await broadcast.broadcast_log(f"🏆 NOVO RECORDE! {player_name} fez {score} pts no {game_type}!", "success")
        else:
            await broadcast.broadcast_log(f"🎮 {player_name} entrou no TOP {rank} com {score} pts!", "info")

    return {
        "success": True,
        "score_id": game_score.id,
        "rank": rank
    }


# ============================================================================
# Admin Endpoints (adding projects)
# ============================================================================
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
# Live Mode Control (Start/Stop)
# ============================================================================

@router.get("/admin/live-mode")
async def get_live_mode_status(db: AsyncSession = Depends(get_db)):
    """Get current live mode status based on kanban state."""
    # Live mode is active if there are cards being processed (not in backlog or done)
    processing_columns = ['plan', 'implement', 'test', 'review']

    result = await db.execute(
        select(func.count(Card.id))
        .where(Card.column_id.in_(processing_columns))
    )
    cards_in_progress = result.scalar() or 0

    return {
        "active": cards_in_progress > 0,
        "cards_in_progress": cards_in_progress,
        "projects_path": LIVE_PROJECTS_PATH
    }


# Contador de projetos para gerar folders únicos
_project_counter = 0


async def _clear_pending_goals() -> None:
    from ..database import async_session_maker
    from sqlalchemy import delete

    async with async_session_maker() as session:
        await session.execute(delete(Goal).where(Goal.status == GoalStatus.PENDING))
        await session.commit()


def _read_live_started_at() -> Optional[datetime]:
    if not os.path.exists(LIVE_STARTED_AT_PATH):
        return None
    try:
        value = Path(LIVE_STARTED_AT_PATH).read_text().strip()
    except OSError:
        return None
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _write_live_started_at() -> datetime:
    started_at = datetime.utcnow()
    Path(LIVE_STARTED_AT_PATH).write_text(started_at.isoformat())
    return started_at


def _clear_live_started_at() -> None:
    try:
        os.remove(LIVE_STARTED_AT_PATH)
    except FileNotFoundError:
        pass


async def _select_ai_project() -> dict:
    from ..services.orchestrator_service import get_orchestrator_service
    import re

    orchestrator = get_orchestrator_service()
    history = orchestrator.read_project_history()
    history_set = {h.lower() for h in history}

    for _ in range(3):
        project = await orchestrator.decide_next_project(history)
        if not project or not project.get("title"):
            continue
        if project["title"].lower() in history_set:
            continue

        category_raw = project.get("category") or project["title"]
        category = re.sub(r"[^a-z0-9-]", "", category_raw.lower()) or "projeto-live"

        return {
            "id": category,
            "title": project["title"],
            "description": project.get("description") or "",
        }

    raise HTTPException(status_code=500, detail="Nao foi possivel escolher um novo projeto")


async def _start_project_by_id(project_id: str, title: str = None, description: str = None) -> dict:
    """Internal function to start a project by its ID or AI-generated data."""
    global _project_counter

    _project_counter += 1

    await _clear_pending_goals()

    import re
    base_name = project_id or title or "projeto-live"
    safe_name = re.sub(r'[^a-zA-Z0-9-]', '', base_name.lower().replace(' ', '-'))[:20]
    project_folder = f"projeto{_project_counter}-{safe_name or 'ai-project'}"
    project_title = title or project_id or "Projeto"
    project_desc = description or f"Projeto gerado pela IA: {project_title}"
    project = {
        "id": project_id or safe_name,
        "title": project_title,
        "description": project_desc,
        "folder": safe_name or 'ai-project'
    }

    project_path = os.path.join(LIVE_PROJECTS_PATH, project_folder)

    # Create project directory
    os.makedirs(project_path, exist_ok=True)

    # Set as active project (specific project folder)
    from ..models.project import ActiveProject
    from ..database import async_session_maker
    from sqlalchemy import delete

    async with async_session_maker() as session:
        await session.execute(delete(ActiveProject))
        live_project = ActiveProject(
            id=project_folder,
            path=project_path,
            name=f"Live: {project['title']}",
            has_claude_config=False,
            claude_config_path=None,
        )
        session.add(live_project)
        await session.commit()

    # Get orchestrator and submit goal
    from ..services.orchestrator_service import get_orchestrator_service

    orchestrator = get_orchestrator_service()
    prompt = LIVE_MODE_PROMPT.format(
        project_type=project["title"],
        project_path=project_path
    )

    result = await orchestrator.submit_goal(
        description=prompt,
        source="live_mode_auto",
        source_id=f"{project_folder}|{project['title']}|{project.get('id', '')}"  # folder|title|category
    )

    # Broadcast
    broadcast = get_live_broadcast_service()
    await broadcast.update_status(is_working=True, current_stage="starting", live_started_at=_read_live_started_at())
    await broadcast.broadcast_log(f"🚀 Starting: {project['title']}", "success")
    await broadcast.broadcast_log(f"📁 Path: {project_path}", "info")

    return {
        "success": True,
        "project": project,
        "project_folder": project_folder
    }


@router.post("/admin/live-mode/start")
async def start_live_mode(
    project_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Start live mode - submit the entertainment goal to orchestrator."""
    global _project_counter

    # Check if there are cards already being processed
    processing_columns = ['plan', 'implement', 'test', 'review']
    result = await db.execute(
        select(func.count(Card.id))
        .where(Card.column_id.in_(processing_columns))
    )
    cards_in_progress = result.scalar() or 0

    if cards_in_progress > 0:
        raise HTTPException(status_code=400, detail=f"Live mode is already active ({cards_in_progress} cards in progress)")

    # Set active project to live-projects directory
    from ..models.project import ActiveProject
    from ..database import async_session_maker
    from sqlalchemy import delete
    import os

    project = await _select_ai_project()
    live_started_at = _write_live_started_at()
    await _clear_pending_goals()
    _project_counter += 1
    project_folder = f"projeto{_project_counter}-{project['id']}"
    project_path = os.path.join(LIVE_PROJECTS_PATH, project_folder)

    # Create project directory
    os.makedirs(project_path, exist_ok=True)
    print(f"[LiveMode] Created project folder: {project_path}")

    # Set as active project (specific project folder, not root)
    async with async_session_maker() as session:
        # Clear previous active projects
        await session.execute(delete(ActiveProject))

        # Create live project entry with specific project path
        live_project = ActiveProject(
            id=project_folder,
            path=project_path,
            name=f"Live: {project['title']}",
            has_claude_config=False,
            claude_config_path=None,
        )
        session.add(live_project)
        await session.commit()
        print(f"[LiveMode] Set active project to: {project_path}")

    # Import orchestrator service
    from ..services.orchestrator_service import get_orchestrator_service

    # Get orchestrator
    orchestrator = get_orchestrator_service()

    # Format prompt with project details
    prompt = LIVE_MODE_PROMPT.format(
        project_type=project["title"],
        project_path=project_path
    )

    # Submit as a new goal (source_id stores project info for later)
    try:
        result = await orchestrator.submit_goal(
            description=prompt,
            source="live_mode_auto",
            source_id=f"{project_folder}|{project['title']}|{project.get('id', '')}"  # folder|title|category
        )
        goal_id = result.get("goal_id") if isinstance(result, dict) else str(result)

        # Broadcast status update
        broadcast = get_live_broadcast_service()
        await broadcast.update_status(is_working=True, current_stage="starting", live_started_at=live_started_at)
        await broadcast.broadcast_log(f"🚀 Iniciando projeto: {project['title']}", "success")
        await broadcast.broadcast_log(f"📁 Pasta: {project_folder}", "info")

        return {
            "success": True,
            "message": "Live mode started",
            "goal_id": goal_id,
            "project": project,
            "project_folder": project_folder,
            "projects_path": LIVE_PROJECTS_PATH
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start live mode: {str(e)}")


@router.post("/admin/live-mode/stop")
async def stop_live_mode(db: AsyncSession = Depends(get_db)):
    """Stop live mode - moves all in-progress cards back to backlog."""
    # Check if there are cards being processed
    processing_columns = ['plan', 'implement', 'test', 'review']
    result = await db.execute(
        select(func.count(Card.id))
        .where(Card.column_id.in_(processing_columns))
    )
    cards_in_progress = result.scalar() or 0

    if cards_in_progress == 0:
        raise HTTPException(status_code=400, detail="Live mode is not active")

    # Move all in-progress cards back to backlog
    await db.execute(
        update(Card)
        .where(Card.column_id.in_(processing_columns))
        .values(column_id='backlog')
    )
    await db.commit()

    # Broadcast status update
    broadcast = get_live_broadcast_service()
    _clear_live_started_at()
    await broadcast.update_status(is_working=False, current_stage=None, live_started_at=None)
    await broadcast.broadcast_log(f"Live mode stopped. {cards_in_progress} cards moved to backlog.", "info")

    return {
        "success": True,
        "message": f"Live mode stopped. {cards_in_progress} cards moved to backlog."
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

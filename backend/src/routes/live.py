"""Live spectator routes and WebSocket."""

import asyncio
import json
import logging
import os
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
from ..models.live import Vote, VoteType, CompletedProject, GameScore
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
# Live Mode Configuration
# ============================================================================

LIVE_PROJECTS_PATH = os.environ.get("LIVE_PROJECTS_PATH", "/opt/zenflow/live-projects")

LIVE_MODE_PROMPT = """⚠️ IMPORTANTE: CRIE APENAS 1 CARD. NÃO DECOMPONHA!

Projeto: {project_type}
Pasta do projeto: {project_path}/

## Objetivo da live (entretenimento)
- Precisa ser divertido de assistir ao vivo.
- Tem que ter impacto visual/sonoro imediato.
- Incluir um "wow moment" nos primeiros 2-3 minutos.
- Preferir interatividade (mouse/teclado/gestos) e feedback instantaneo.
- Evitar temas repetidos da live (na duvida, escolha algo diferente).

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


@router.get("/voting", response_model=VotingStateResponse)
async def get_voting_state():
    """Get current voting state."""
    voting = get_voting_service()
    from ..database import async_session_maker
    async with async_session_maker() as db:
        await voting.refresh_state(db)
    return voting.get_state()


@router.post("/vote", response_model=VoteResponse)
async def cast_vote(
    request: VoteRequest,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """Cast a vote for the next project."""
    voting = get_voting_service()
    await voting.refresh_state(db)

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
# Admin Endpoints (for starting voting, adding projects)
# ============================================================================

@router.post("/admin/start-voting")
async def admin_start_voting(
    duration_seconds: int = 60,
    db: AsyncSession = Depends(get_db)
):
    """Start a new voting round with project options (admin only)."""
    voting = get_voting_service()
    broadcast = get_live_broadcast_service()

    await voting.refresh_state(db)

    if voting.is_active:
        raise HTTPException(status_code=400, detail="Voting is already active")

    # Use a random slice of PROJECT_OPTIONS as voting options
    import random
    sample_size = min(VOTING_OPTIONS_PER_ROUND, len(PROJECT_OPTIONS))
    sampled = random.sample(PROJECT_OPTIONS, sample_size)
    voting_options = [
        {
            "title": p["title"],
            "description": p["description"],
            "category": p["id"],  # Use id as category for mapping back
        }
        for p in sampled
    ]

    round, options = await voting.start_round(db, duration_seconds, voting_options)

    # Broadcast voting started to live spectators
    await broadcast.broadcast_voting_started(
        options=[
            {"id": o.id, "title": o.title, "description": o.description, "vote_count": 0}
            for o in options
        ],
        ends_at=round.ends_at.isoformat(),
        duration_seconds=duration_seconds
    )

    await broadcast.broadcast_log(f"🗳️ VOTING STARTED! {duration_seconds}s to vote!", "success")

    return {
        "success": True,
        "round_id": round.id,
        "ends_at": round.ends_at.isoformat(),
        "duration_seconds": duration_seconds,
        "options": [
            {"id": o.id, "title": o.title, "category": o.category, "description": o.description}
            for o in options
        ]
    }


@router.post("/admin/end-voting")
async def admin_end_voting(db: AsyncSession = Depends(get_db)):
    """End current voting round early (admin only)."""
    voting = get_voting_service()
    await voting.refresh_state(db)

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


# Opções de projetos para votação
VOTING_OPTIONS_PER_ROUND = 7

PROJECT_OPTIONS = [
    {"id": "snake", "title": "🐍 Jogo da Cobrinha Neon", "description": "Snake classico com rastro neon e efeitos", "folder": "snake-game"},
    {"id": "memory", "title": "🎯 Jogo da Memoria Turbo", "description": "Pares de cartas com animacao flip", "folder": "memory-game"},
    {"id": "quiz", "title": "🎮 Quiz Interativo", "description": "Perguntas rapidas com placar ao vivo", "folder": "quiz-game"},
    {"id": "rhythm", "title": "🥁 Jogo de Ritmo", "description": "Notas caindo e acerto no tempo", "folder": "rhythm-game"},
    {"id": "pong", "title": "🏓 Pong Arena", "description": "Pong moderno com boosts e particulas", "folder": "pong-arena"},
    {"id": "reaction", "title": "⚡ Teste de Reacao", "description": "Clique no momento certo e veja o ranking", "folder": "reaction-test"},
    {"id": "typing", "title": "⌨️ Desafio de Digitacao", "description": "Frases rapidas com timer e WPM", "folder": "typing-challenge"},
    {"id": "maze", "title": "🧭 Labirinto Vivo", "description": "Labirinto animado com trilha luminosa", "folder": "live-maze"},
    {"id": "soundboard", "title": "🔊 Soundboard Divertido", "description": "Botoes sonoros com visual divertido", "folder": "soundboard"},
    {"id": "piano", "title": "🎹 Piano Virtual", "description": "Piano tocavel pelo teclado", "folder": "virtual-piano"},
    {"id": "drum", "title": "🥁 Bateria Virtual", "description": "Pads com efeitos e gravacao rapida", "folder": "drum-pad"},
    {"id": "particles", "title": "✨ Arte de Particulas", "description": "Particulas reagindo ao mouse", "folder": "particle-art"},
    {"id": "fractal", "title": "🌀 Fractal Hipnotico", "description": "Zoom em fractais com cores vivas", "folder": "fractal-viewer"},
    {"id": "nebula", "title": "🌌 Nebulosa Generativa", "description": "Ruido e gradientes animados", "folder": "nebula-art"},
    {"id": "boids", "title": "🕊️ Flock Simulation", "description": "Passaros (boids) seguindo regras simples", "folder": "boids-sim"},
    {"id": "orbit", "title": "🪐 Mini Sistema Solar", "description": "Orbits, gravidade fake e brilho", "folder": "solar-sim"},
    {"id": "flowfield", "title": "🧠 Flow Field Art", "description": "Linhas organicas seguindo vetores", "folder": "flow-field"},
    {"id": "fireworks", "title": "🎆 Fogos Interativos", "description": "Explosoes com clique e audio", "folder": "fireworks"},
    {"id": "meme", "title": "😂 Meme Generator Live", "description": "Texto, stickers e export rapido", "folder": "meme-generator"},
    {"id": "dance", "title": "🕺 Boneco Dançarino", "description": "Animacao com ritmo e cores", "folder": "dancing-bot"},
    {"id": "voiceviz", "title": "🎤 Visualizador de Audio", "description": "Bars e ondas reagindo ao microfone", "folder": "audio-visualizer"},
    {"id": "weather", "title": "🌤️ App de Clima Show", "description": "Clima com ilustracoes animadas", "folder": "weather-app"},
    {"id": "pomodoro", "title": "🍅 Pomodoro Cinematico", "description": "Timer com cenas e progresso bonito", "folder": "pomodoro-timer"},
    {"id": "calculator", "title": "🧮 Calculadora Bonita", "description": "Calculadora com design moderno", "folder": "calculator"},
    {"id": "todo", "title": "📝 Todo List Elegante", "description": "Lista de tarefas com animacoes", "folder": "todo-list"},
    {"id": "glitch", "title": "📺 Glitch Studio", "description": "Efeitos glitch e scanlines", "folder": "glitch-studio"},
    {"id": "lens", "title": "🔍 Lente Magica", "description": "Efeito lupa com distorcao", "folder": "magic-lens"},
    {"id": "cards", "title": "🃏 Cartas Magicas", "description": "Cartas que viram e brilham", "folder": "magic-cards"},
]

# Contador de projetos para gerar folders únicos
_project_counter = 0


async def _start_project_by_id(project_id: str, title: str = None, description: str = None) -> dict:
    """Internal function to start a project by its ID or AI-generated data. Called after voting ends."""
    global _project_counter

    # Find project in predefined options
    project = next((p for p in PROJECT_OPTIONS if p["id"] == project_id), None)

    _project_counter += 1

    if project:
        # Use predefined project
        project_folder = f"projeto{_project_counter}-{project['folder']}"
        project_title = project["title"]
        project_desc = project.get("description", "")
    else:
        # AI-generated project - use the title/description passed or create from id
        import re
        # Create folder name from category/id
        safe_name = re.sub(r'[^a-zA-Z0-9-]', '', project_id.lower().replace(' ', '-'))[:20]
        project_folder = f"projeto{_project_counter}-{safe_name or 'ai-project'}"
        project_title = title or project_id
        project_desc = description or f"Projeto gerado pela IA: {project_title}"
        project = {
            "id": project_id,
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
        source="live_mode_voting",
        source_id=f"{project_folder}|{project['title']}|{project.get('id', '')}"  # folder|title|category
    )

    # Broadcast
    broadcast = get_live_broadcast_service()
    await broadcast.update_status(is_working=True, current_stage="starting")
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
    import random

    # Selecionar projeto (passado ou aleatório)
    if project_type:
        project = next((p for p in PROJECT_OPTIONS if p["id"] == project_type), None)
        if not project:
            project = random.choice(PROJECT_OPTIONS)
    else:
        # Primeiro projeto é aleatório
        project = random.choice(PROJECT_OPTIONS)

    _project_counter += 1
    project_folder = f"projeto{_project_counter}-{project['folder']}"
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
            source="live_mode",
            source_id=f"{project_folder}|{project['title']}|{project.get('id', '')}"  # folder|title|category
        )
        goal_id = result.get("goal_id") if isinstance(result, dict) else str(result)

        # Broadcast status update
        broadcast = get_live_broadcast_service()
        await broadcast.update_status(is_working=True, current_stage="starting")
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
    await broadcast.update_status(is_working=False, current_stage=None)
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


# ============================================================================
# Voting Callback - Start winning project after voting ends
# ============================================================================

async def _on_voting_ended(winner, all_options):
    """Callback when voting round ends - start the winning project."""
    if not winner:
        return

    broadcast = get_live_broadcast_service()

    # Broadcast results
    await broadcast.broadcast({
        "type": "voting_ended",
        "winner": {
            "id": winner.id,
            "title": winner.title,
            "description": winner.description,
            "vote_count": winner.vote_count
        },
        "results": [
            {"id": o.id, "title": o.title, "vote_count": o.vote_count}
            for o in all_options
        ]
    })

    await broadcast.broadcast_log(f"🏆 Vencedor: {winner.title} ({winner.vote_count} votos)!", "success")

    # Small delay before starting
    import asyncio
    await asyncio.sleep(3)

    # Start the winning project using its category (which maps to project id)
    # Pass title and description for AI-generated projects
    try:
        await broadcast.broadcast_log(f"🚀 Iniciando projeto: {winner.title}...", "info")
        await _start_project_by_id(
            project_id=winner.category,
            title=winner.title,
            description=winner.description
        )
    except Exception as e:
        await broadcast.broadcast_log(f"❌ Erro ao iniciar projeto: {e}", "error")


# Register the callback when module loads
def _register_voting_callback():
    """Register voting ended callback."""
    voting = get_voting_service()
    voting.on_ended(_on_voting_ended)


# Call registration
_register_voting_callback()

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import update, select
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from .agent import execute_plan, execute_implement, execute_test_implementation, execute_review, get_execution, get_all_executions
from .git_workspace import GitWorkspaceManager
from .database import create_tables
from .repositories.execution_repository import ExecutionRepository
from .models.execution import Execution
from .execution import (
    ExecutePlanRequest,
    ExecutePlanResponse,
    ExecuteImplementRequest,
    ExecuteImplementResponse,
    ExecutionsResponse,
    HealthResponse,
    LogsResponse,
)
from pydantic import BaseModel
from .routes.cards import router as cards_router
from .routes.images import router as images_router
from .routes.projects import router as projects_router
from .routes.chat import router as chat_router
from .routes.execution_ws import router as execution_ws_router
from .routes.activities import router as activities_router
from .database import get_db, async_session_maker
from .repositories.card_repository import CardRepository
from .schemas.card import CardUpdate

# Import models to register them with SQLAlchemy
from .models.card import Card  # noqa: F401
from .models.project import ActiveProject  # noqa: F401


# Schema for workflow state update
class WorkflowStateUpdate(BaseModel):
    stage: str
    error: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Create database tables
    print("[Server] Creating database tables...")
    await create_tables()
    print("[Server] Database tables created successfully")
    yield
    # Shutdown: cleanup if needed
    print("[Server] Shutting down...")


app = FastAPI(
    title="Kanban Agent Server",
    description="Backend server for Kanban + Claude Agent SDK integration",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cards_router)
app.include_router(images_router)
app.include_router(projects_router)
app.include_router(chat_router)
app.include_router(execution_ws_router)
app.include_router(activities_router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
    )


@app.post("/api/execute-plan", response_model=ExecutePlanResponse)
async def execute_plan_endpoint(request: ExecutePlanRequest):
    """Execute a plan."""
    # Validate request
    if not request.card_id or not request.title:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: cardId and title are required",
        )

    print(f"[Server] Received plan request for card: {request.card_id}")
    print(f"[Server] Title: {request.title}")
    print(f"[Server] Description: {request.description or '(none)'}")

    try:
        # Use parent directory as working directory (the main project)
        cwd = str(Path.cwd().parent)

        # Buscar card do banco para obter o modelo configurado e imagens
        async with async_session_maker() as session:
            repo = CardRepository(session)
            card = await repo.get_by_id(request.card_id)
            model = card.model_plan if card else "opus-4.5"
            images = card.images if card else None

        # Passar db_session para persistir logs
        async with async_session_maker() as db_session:
            result = await execute_plan(
                card_id=request.card_id,
                title=request.title,
                description=request.description or "",
                cwd=cwd,
                model=model,
                images=images,
                db_session=db_session,
            )

        if result.success:
            # Save spec_path to database if available
            if result.spec_path:
                async with async_session_maker() as session:
                    repo = CardRepository(session)
                    await repo.update_spec_path(request.card_id, result.spec_path)
                    await session.commit()

            return ExecutePlanResponse(
                success=True,
                cardId=request.card_id,
                result=result.result,
                logs=result.logs,
                specPath=result.spec_path,
            )
        else:
            error_response = ExecutePlanResponse(
                success=False,
                cardId=request.card_id,
                error=result.error,
                logs=result.logs,
            )
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(by_alias=True),
            )

    except Exception as e:
        error_message = str(e)
        print(f"[Server] Error: {error_message}")
        error_response = ExecutePlanResponse(
            success=False,
            cardId=request.card_id,
            error=error_message,
            logs=[],
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(by_alias=True),
        )


@app.post("/api/execute-implement", response_model=ExecuteImplementResponse)
async def execute_implement_endpoint(request: ExecuteImplementRequest):
    """Execute /implement command with spec path."""
    # Validate request
    if not request.card_id or not request.spec_path:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: cardId and specPath are required",
        )

    print(f"[Server] Received implement request for card: {request.card_id}")
    print(f"[Server] Spec path: {request.spec_path}")

    try:
        # Use parent directory as working directory (the main project)
        cwd = str(Path.cwd().parent)

        # Buscar card do banco para obter o modelo configurado e imagens
        # Mantém sessão aberta para passar ao execute_implement
        async with async_session_maker() as session:
            repo = CardRepository(session)
            card = await repo.get_by_id(request.card_id)
            model = card.model_implement if card else "opus-4.5"
            images = card.images if card else None

            result = await execute_implement(
                card_id=request.card_id,
                spec_path=request.spec_path,
                cwd=cwd,
                model=model,
                images=images,
                db_session=session,
            )

        if result.success:
            return ExecuteImplementResponse(
                success=True,
                cardId=request.card_id,
                result=result.result,
                logs=result.logs,
            )
        else:
            error_response = ExecuteImplementResponse(
                success=False,
                cardId=request.card_id,
                error=result.error,
                logs=result.logs,
            )
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(by_alias=True),
            )

    except Exception as e:
        error_message = str(e)
        print(f"[Server] Error: {error_message}")
        error_response = ExecuteImplementResponse(
            success=False,
            cardId=request.card_id,
            error=error_message,
            logs=[],
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(by_alias=True),
        )


@app.post("/api/execute-test", response_model=ExecuteImplementResponse)
async def execute_test_endpoint(request: ExecuteImplementRequest):
    """Execute /test-implementation command with spec path."""
    if not request.card_id or not request.spec_path:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: cardId and specPath are required",
        )

    print(f"[Server] Received test request for card: {request.card_id}")
    print(f"[Server] Spec path: {request.spec_path}")

    try:
        cwd = str(Path.cwd().parent)

        # Buscar card do banco para obter o modelo configurado e imagens
        # Mantém sessão aberta para passar ao execute_test_implementation
        async with async_session_maker() as session:
            repo = CardRepository(session)
            card = await repo.get_by_id(request.card_id)
            model = card.model_test if card else "opus-4.5"
            images = card.images if card else None

            result = await execute_test_implementation(
                card_id=request.card_id,
                spec_path=request.spec_path,
                cwd=cwd,
                model=model,
                images=images,
                db_session=session,
            )

        if result.success:
            return ExecuteImplementResponse(
                success=True,
                cardId=request.card_id,
                result=result.result,
                logs=result.logs,
            )
        else:
            error_response = ExecuteImplementResponse(
                success=False,
                cardId=request.card_id,
                error=result.error,
                logs=result.logs,
            )
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(by_alias=True),
            )

    except Exception as e:
        error_message = str(e)
        print(f"[Server] Error: {error_message}")
        error_response = ExecuteImplementResponse(
            success=False,
            cardId=request.card_id,
            error=error_message,
            logs=[],
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(by_alias=True),
        )


@app.post("/api/execute-review", response_model=ExecuteImplementResponse)
async def execute_review_endpoint(request: ExecuteImplementRequest):
    """Execute /review command with spec path."""
    if not request.card_id or not request.spec_path:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: cardId and specPath are required",
        )

    print(f"[Server] Received review request for card: {request.card_id}")
    print(f"[Server] Spec path: {request.spec_path}")

    try:
        cwd = str(Path.cwd().parent)

        # Buscar card do banco para obter o modelo configurado e imagens
        # Mantém sessão aberta para passar ao execute_review
        async with async_session_maker() as session:
            repo = CardRepository(session)
            card = await repo.get_by_id(request.card_id)
            model = card.model_review if card else "opus-4.5"
            images = card.images if card else None

            result = await execute_review(
                card_id=request.card_id,
                spec_path=request.spec_path,
                cwd=cwd,
                model=model,
                images=images,
                db_session=session,
            )

        if result.success:
            return ExecuteImplementResponse(
                success=True,
                cardId=request.card_id,
                result=result.result,
                logs=result.logs,
            )
        else:
            error_response = ExecuteImplementResponse(
                success=False,
                cardId=request.card_id,
                error=result.error,
                logs=result.logs,
            )
            return JSONResponse(
                status_code=500,
                content=error_response.model_dump(by_alias=True),
            )

    except Exception as e:
        error_message = str(e)
        print(f"[Server] Error: {error_message}")
        error_response = ExecuteImplementResponse(
            success=False,
            cardId=request.card_id,
            error=error_message,
            logs=[],
        )
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(by_alias=True),
        )


@app.patch("/api/cards/{card_id}/workflow-state")
async def update_workflow_state(
    card_id: str,
    state: WorkflowStateUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza o estado do workflow para um card"""
    repo = ExecutionRepository(db)

    # Busca execução ativa
    execution = await repo.get_active_execution(card_id)

    if not execution:
        # Cria nova execução se não existir
        execution = await repo.create_execution(
            card_id=card_id,
            command="workflow",
            title="Workflow Automation"
        )

    # Atualiza workflow stage
    await db.execute(
        update(Execution)
        .where(Execution.id == execution.id)
        .values(
            workflow_stage=state.stage,
            workflow_error=state.error
        )
    )
    await db.commit()

    return {"success": True, "stage": state.stage}


@app.get("/api/logs/{card_id}", response_model=LogsResponse)
async def get_logs_endpoint(card_id: str, db: AsyncSession = Depends(get_db)):
    """Get execution logs from database"""
    repo = ExecutionRepository(db)
    execution = await repo.get_execution_with_logs(card_id)

    if not execution:
        # Fallback para memória se não houver no banco
        execution = await get_execution(card_id)
        if not execution:
            return LogsResponse(
                success=False,
                error="No execution found for this card",
            )

    return LogsResponse(
        success=True,
        execution=execution,
    )


@app.get("/api/logs/{card_id}/history")
async def get_logs_history_endpoint(card_id: str, db: AsyncSession = Depends(get_db)):
    """Get full execution history for a card"""
    repo = ExecutionRepository(db)
    history = await repo.get_execution_history(card_id)

    return {
        "success": True,
        "cardId": card_id,
        "history": history
    }


# ============================================================================
# Git Worktree Isolation Endpoints
# ============================================================================

async def get_active_project(db: AsyncSession):
    """Helper to get the currently active project."""
    result = await db.execute(
        select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


@app.post("/api/cards/{card_id}/workspace")
async def create_card_workspace(
    card_id: str,
    request_body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db)
):
    """Cria worktree isolado para o card."""

    # Obter projeto ativo
    project = await get_active_project(db)
    if not project:
        raise HTTPException(status_code=400, detail="No active project")

    # Verificar se projeto eh um repo git
    git_dir = Path(project.path) / ".git"
    if not git_dir.exists():
        raise HTTPException(
            status_code=400,
            detail="Project is not a git repository. Worktrees disabled."
        )

    # Pegar base_branch do request body ou do card
    base_branch = None
    if request_body and "baseBranch" in request_body:
        base_branch = request_body["baseBranch"]
    else:
        # Tentar pegar do card
        card_repo = CardRepository(db)
        card = await card_repo.get_by_id(card_id)
        if card and card.base_branch:
            base_branch = card.base_branch

    # Criar worktree
    git_manager = GitWorkspaceManager(project.path)
    await git_manager.recover_state()  # Garantir estado limpo
    result = await git_manager.create_worktree(card_id, base_branch)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    # Atualizar card diretamente
    card_repo = CardRepository(db)
    update_data = CardUpdate(
        branch_name=result.branch_name,
        worktree_path=result.worktree_path
    )
    await card_repo.update(card_id, update_data)
    await db.commit()

    return {
        "success": True,
        "branchName": result.branch_name,
        "worktreePath": result.worktree_path
    }


@app.get("/api/branches")
async def list_active_branches(db: AsyncSession = Depends(get_db)):
    """Lista todas as branches/worktrees ativos."""

    project = await get_active_project(db)
    if not project:
        raise HTTPException(status_code=400, detail="No active project")

    git_manager = GitWorkspaceManager(project.path)
    worktrees = await git_manager.list_active_worktrees()

    # Enriquecer com dados dos cards
    enriched = []

    for wt in worktrees:
        branch = wt.get('branch', '')
        if branch.startswith('agent/'):
            # Buscar card pelo branch_name
            result = await db.execute(
                select(Card).where(Card.branch_name == branch)
            )
            card = result.scalar_one_or_none()

            if card:
                enriched.append({
                    "branch": branch,
                    "path": wt['path'],
                    "cardId": card.id,
                    "cardTitle": card.title,
                    "cardColumn": card.column_id
                })

    return {"branches": enriched}


@app.post("/api/cleanup-orphan-worktrees")
async def cleanup_orphan_worktrees(db: AsyncSession = Depends(get_db)):
    """Remove worktrees orfaos."""

    project = await get_active_project(db)
    if not project:
        raise HTTPException(status_code=400, detail="No active project")

    # Obter IDs de cards ativos
    result = await db.execute(select(Card.id))
    active_card_ids = [row[0] for row in result.fetchall()]

    git_manager = GitWorkspaceManager(project.path)
    removed = await git_manager.cleanup_orphan_worktrees(active_card_ids)

    return {"success": True, "removedCount": removed}


@app.get("/api/git/branches")
async def list_git_branches():
    """Lista todas as branches do repositório git."""

    # Buscar projeto ativo do banco auth.db (onde é salvo)
    async with async_session_maker() as session:
        result = await session.execute(
            select(ActiveProject).order_by(ActiveProject.loaded_at.desc()).limit(1)
        )
        project = result.scalar_one_or_none()

    # Se não houver projeto ativo, usar diretório raiz
    if project:
        project_path = project.path
    else:
        # Fallback: diretório raiz (2 níveis acima do backend/src)
        project_path = str(Path(__file__).parent.parent.parent)

    # Verificar se é repositório git
    git_dir = Path(project_path) / ".git"
    if not git_dir.exists():
        return {"success": True, "branches": [], "defaultBranch": "main"}

    git_manager = GitWorkspaceManager(project_path)
    branches = await git_manager.list_all_branches()

    return {
        "success": True,
        "branches": branches,
        "defaultBranch": await git_manager._get_default_branch()
    }


def main():
    """Run the server."""
    import uvicorn

    port = int(os.environ.get("PORT", 3001))
    print(f"[Server] Agent server running on http://localhost:{port}")
    print("[Server] Endpoints:")
    print("  - GET  /health")
    print("  - GET  /api/logs/:cardId")
    print("  - GET  /api/executions")
    print("  - POST /api/execute-plan")
    print("  - POST /api/execute-implement")
    print("  - POST /api/execute-test")
    print("  - POST /api/execute-review")
    print("  - GET  /api/cards")
    print("  - POST /api/cards")
    print("  - GET  /api/cards/:id")
    print("  - PUT  /api/cards/:id")
    print("  - DELETE /api/cards/:id")
    print("  - PATCH /api/cards/:id/move")
    print("  - POST /api/images/upload")
    print("  - GET  /api/images/:id")
    print("  - DELETE /api/images/:id")
    print("  - POST /api/images/cleanup")
    print("  - POST /api/chat/sessions")
    print("  - GET  /api/chat/sessions/:id")
    print("  - DELETE /api/chat/sessions/:id")
    print("  - WS   /api/chat/ws/:sessionId")
    print("  - WS   /api/execution/ws/:cardId")
    print("  - POST /api/cards/:id/workspace")
    print("  - GET  /api/branches")
    print("  - POST /api/cleanup-orphan-worktrees")

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

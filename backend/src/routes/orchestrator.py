"""Routes for orchestrator API."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas.orchestrator import (
    GoalCreate,
    GoalResponse,
    GoalListResponse,
    ActionResponse,
    LogListResponse,
    LogEntry,
    OrchestratorStatus,
    OrchestratorStartResponse,
    OrchestratorStopResponse,
    LearningListResponse,
    LearningResponse,
    LearningQueryRequest,
    OrchestratorStats,
)
from ..services.orchestrator_service import get_orchestrator_service
from ..services.orchestrator_logger import get_orchestrator_logger
from ..services.qdrant_service import get_qdrant_service
from ..repositories.orchestrator_repository import GoalRepository, ActionRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


# ==================== ORCHESTRATOR CONTROL ====================

@router.get("/status", response_model=OrchestratorStatus)
async def get_status(db: AsyncSession = Depends(get_db)):
    """Get current orchestrator status."""
    service = get_orchestrator_service(db)
    status = service.get_status()
    return OrchestratorStatus(**status)


@router.post("/start", response_model=OrchestratorStartResponse)
async def start_orchestrator(db: AsyncSession = Depends(get_db)):
    """Start the orchestrator loop."""
    service = get_orchestrator_service(db)

    if service.is_running():
        return OrchestratorStartResponse(
            success=False,
            message="Orchestrator is already running"
        )

    await service.start()
    return OrchestratorStartResponse(
        success=True,
        message="Orchestrator started"
    )


@router.post("/stop", response_model=OrchestratorStopResponse)
async def stop_orchestrator(db: AsyncSession = Depends(get_db)):
    """Stop the orchestrator loop."""
    service = get_orchestrator_service(db)

    if not service.is_running():
        return OrchestratorStopResponse(
            success=False,
            message="Orchestrator is not running"
        )

    await service.stop()
    return OrchestratorStopResponse(
        success=True,
        message="Orchestrator stopped"
    )


# ==================== GOALS ====================

@router.post("/goals", response_model=GoalResponse)
async def create_goal(
    goal_data: GoalCreate,
    db: AsyncSession = Depends(get_db)
):
    """Submit a new goal to the orchestrator."""
    service = get_orchestrator_service(db)
    result = await service.submit_goal(
        description=goal_data.description,
        source=goal_data.source,
        source_id=goal_data.source_id,
    )

    goal_repo = GoalRepository(db)
    goal = await goal_repo.get_by_id(result["id"])

    if not goal:
        raise HTTPException(status_code=500, detail="Failed to create goal")

    return GoalResponse.model_validate(goal)


@router.get("/goals", response_model=GoalListResponse)
async def list_goals(
    include_completed: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List all goals."""
    goal_repo = GoalRepository(db)
    goals = await goal_repo.get_all(include_completed=include_completed)

    return GoalListResponse(
        goals=[GoalResponse.model_validate(g) for g in goals],
        total=len(goals)
    )


@router.get("/goals/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific goal."""
    goal_repo = GoalRepository(db)
    goal = await goal_repo.get_by_id(goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return GoalResponse.model_validate(goal)


@router.get("/goals/{goal_id}/actions", response_model=list[ActionResponse])
async def get_goal_actions(
    goal_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all actions for a goal."""
    action_repo = ActionRepository(db)
    actions = await action_repo.get_by_goal(goal_id)

    return [ActionResponse.model_validate(a) for a in actions]


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a goal."""
    goal_repo = GoalRepository(db)
    success = await goal_repo.delete(goal_id)

    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {"success": True, "message": "Goal deleted"}


# ==================== LOGS ====================

@router.get("/logs", response_model=LogListResponse)
async def get_logs(
    limit: int = 50,
):
    """Get recent orchestrator logs."""
    orch_logger = get_orchestrator_logger()
    logs = orch_logger.read_recent_logs(limit=limit)

    return LogListResponse(
        logs=[
            LogEntry(
                timestamp=log.timestamp,
                level=log.level,
                step=log.step,
                message=log.message,
                goal_id=log.goal_id,
                data=log.data,
            )
            for log in logs
        ],
        total=len(logs)
    )


# ==================== LEARNINGS ====================

@router.post("/learnings/query", response_model=LearningListResponse)
async def query_learnings(request: LearningQueryRequest):
    """Query relevant learnings from long-term memory."""
    qdrant = get_qdrant_service()
    results = qdrant.query_learnings(
        query_text=request.query,
        limit=request.limit,
        score_threshold=request.min_score,
    )

    learnings = [
        LearningResponse(
            id=r["id"],
            goal_description=r.get("goal_description", ""),
            learning=r.get("learning", ""),
            outcome=r.get("outcome", "unknown"),
            cards_created=r.get("cards_created", []),
            timestamp=r.get("timestamp", ""),
            score=r.get("score"),
        )
        for r in results
    ]

    return LearningListResponse(
        learnings=learnings,
        total=len(learnings)
    )


@router.get("/learnings/stats")
async def get_learning_stats():
    """Get statistics about long-term memory."""
    qdrant = get_qdrant_service()
    return qdrant.get_collection_stats()


# ==================== WEBSOCKET ====================

@router.websocket("/ws")
async def orchestrator_websocket(websocket: WebSocket):
    """WebSocket for real-time orchestrator updates."""
    orch_logger = get_orchestrator_logger()
    await orch_logger.connect(websocket)

    try:
        while True:
            # Keep connection alive, handle any incoming messages
            data = await websocket.receive_text()
            # Currently we don't expect messages from client
            # but could add commands in the future

    except WebSocketDisconnect:
        orch_logger.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        orch_logger.disconnect(websocket)


# ==================== STATS ====================

@router.get("/stats", response_model=OrchestratorStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get orchestrator statistics."""
    from ..models.orchestrator import GoalStatus

    goal_repo = GoalRepository(db)
    all_goals = await goal_repo.get_all(include_completed=True)

    total = len(all_goals)
    active = len([g for g in all_goals if g.status == GoalStatus.ACTIVE])
    completed = len([g for g in all_goals if g.status == GoalStatus.COMPLETED])
    failed = len([g for g in all_goals if g.status == GoalStatus.FAILED])

    # Get action count
    action_repo = ActionRepository(db)
    total_actions = 0
    for goal in all_goals:
        actions = await action_repo.get_by_goal(goal.id)
        total_actions += len(actions)

    # Get Qdrant stats
    qdrant = get_qdrant_service()
    collection_stats = None
    try:
        stats = qdrant.get_collection_stats()
        if "error" not in stats:
            collection_stats = stats
    except Exception:
        pass

    return OrchestratorStats(
        total_goals=total,
        active_goals=active,
        completed_goals=completed,
        failed_goals=failed,
        total_actions=total_actions,
        collection_stats=collection_stats,
    )

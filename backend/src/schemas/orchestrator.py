"""Pydantic schemas for orchestrator API."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class GoalStatus(str, Enum):
    """Goal status values."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ActionType(str, Enum):
    """Action type values."""
    VERIFY_LIMIT = "verify_limit"
    DECOMPOSE = "decompose"
    EXECUTE_CARD = "execute_card"
    CREATE_FIX = "create_fix"
    WAIT = "wait"
    COMPLETE_GOAL = "complete_goal"


# ==================== GOAL SCHEMAS ====================

class GoalCreate(BaseModel):
    """Schema for creating a new goal."""
    description: str = Field(..., min_length=1, max_length=2000)
    source: Optional[str] = Field(None, max_length=50)
    source_id: Optional[str] = Field(None, max_length=100)


class GoalResponse(BaseModel):
    """Schema for goal response."""
    id: str
    description: str
    status: GoalStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cards: Optional[List[str]] = None
    learning: Optional[str] = None
    error: Optional[str] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    class Config:
        from_attributes = True


class GoalListResponse(BaseModel):
    """Schema for list of goals."""
    goals: List[GoalResponse]
    total: int


# ==================== ACTION SCHEMAS ====================

class ActionResponse(BaseModel):
    """Schema for action response."""
    id: str
    goal_id: str
    action_type: ActionType
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    card_id: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== LOG SCHEMAS ====================

class LogEntry(BaseModel):
    """Schema for a log entry."""
    timestamp: str
    level: str
    step: str
    message: str
    goal_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class LogListResponse(BaseModel):
    """Schema for list of logs."""
    logs: List[LogEntry]
    total: int


# ==================== STATUS SCHEMAS ====================

class MemoryHealth(BaseModel):
    """Schema for memory health status."""
    short_term: bool
    long_term: bool


class UsageInfo(BaseModel):
    """Schema for Claude usage info."""
    session_used_percent: float
    daily_used_percent: float
    is_safe_to_execute: bool
    error: Optional[str] = None


class OrchestratorStatus(BaseModel):
    """Schema for orchestrator status."""
    running: bool
    loop_interval_seconds: int
    usage_limit_percent: int
    last_usage_check: Optional[UsageInfo] = None
    memory_health: MemoryHealth


class OrchestratorStartResponse(BaseModel):
    """Schema for start response."""
    success: bool
    message: str


class OrchestratorStopResponse(BaseModel):
    """Schema for stop response."""
    success: bool
    message: str


# ==================== LEARNING SCHEMAS ====================

class LearningResponse(BaseModel):
    """Schema for a learning entry."""
    id: str
    goal_description: str
    learning: str
    outcome: str
    cards_created: List[str]
    timestamp: str
    score: Optional[float] = None


class LearningListResponse(BaseModel):
    """Schema for list of learnings."""
    learnings: List[LearningResponse]
    total: int


class LearningQueryRequest(BaseModel):
    """Schema for querying learnings."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(5, ge=1, le=20)
    min_score: float = Field(0.5, ge=0.0, le=1.0)


# ==================== STATS SCHEMAS ====================

class CollectionStats(BaseModel):
    """Schema for Qdrant collection stats."""
    points_count: int
    vectors_count: int
    status: str


class OrchestratorStats(BaseModel):
    """Schema for orchestrator statistics."""
    total_goals: int
    active_goals: int
    completed_goals: int
    failed_goals: int
    total_actions: int
    collection_stats: Optional[CollectionStats] = None

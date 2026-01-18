"""Pydantic schemas for Live Spectator System."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Status Schemas
# ============================================================================

class LiveStatusResponse(BaseModel):
    """Current status of the AI."""
    is_working: bool = Field(description="Whether AI is currently working")
    current_stage: Optional[str] = Field(None, description="Current SDLC stage: plan, implement, test, review")
    current_card: Optional[Dict[str, Any]] = Field(None, description="Current card being worked on")
    progress: Optional[int] = Field(None, description="Progress percentage 0-100")
    spectator_count: int = Field(description="Number of spectators watching")


# ============================================================================
# Card Schemas (Read-only for spectators)
# ============================================================================

class LiveCardResponse(BaseModel):
    """Card info for spectators (read-only, limited info)."""
    id: str
    title: str
    description: Optional[str] = None
    column_id: str
    created_at: datetime


class LiveKanbanResponse(BaseModel):
    """Kanban board state for spectators."""
    columns: Dict[str, List[LiveCardResponse]]
    total_cards: int


# ============================================================================
# Voting Schemas
# ============================================================================

class VotingOptionSchema(BaseModel):
    """A voting option."""
    id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    vote_count: int = 0


class VotingStateResponse(BaseModel):
    """Current voting state."""
    is_active: bool = Field(description="Whether voting is currently active")
    round_id: Optional[str] = None
    options: List[VotingOptionSchema] = []
    ends_at: Optional[datetime] = None
    time_remaining_seconds: Optional[int] = None


class VoteRequest(BaseModel):
    """Request to cast a vote."""
    option_id: str
    session_id: str


class VoteResponse(BaseModel):
    """Response after voting."""
    success: bool
    message: str
    new_vote_count: Optional[int] = None


# ============================================================================
# Project Gallery Schemas
# ============================================================================

class CompletedProjectSchema(BaseModel):
    """Completed project in gallery."""
    id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    screenshot_url: Optional[str] = None
    preview_url: Optional[str] = None
    like_count: int = 0
    completed_at: datetime


class ProjectGalleryResponse(BaseModel):
    """Gallery of completed projects."""
    projects: List[CompletedProjectSchema]
    total: int


class LikeRequest(BaseModel):
    """Request to like a project."""
    session_id: str


class LikeResponse(BaseModel):
    """Response after liking."""
    success: bool
    message: str
    new_like_count: int


# ============================================================================
# WebSocket Message Schemas
# ============================================================================

class WSMessageBase(BaseModel):
    """Base WebSocket message."""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WSPresenceUpdate(WSMessageBase):
    """Spectator count update."""
    type: str = "presence_update"
    spectator_count: int


class WSStatusUpdate(WSMessageBase):
    """AI status update."""
    type: str = "status_update"
    is_working: bool
    current_stage: Optional[str] = None
    current_card: Optional[Dict[str, Any]] = None
    progress: Optional[int] = None


class WSCardUpdate(WSMessageBase):
    """Card moved/updated."""
    type: str = "card_update"
    action: str  # "moved", "created", "updated"
    card: LiveCardResponse
    from_column: Optional[str] = None
    to_column: Optional[str] = None


class WSLogEntry(WSMessageBase):
    """Log entry from AI."""
    type: str = "log_entry"
    content: str
    log_type: Optional[str] = None  # "info", "success", "error", etc.


class WSVotingStarted(WSMessageBase):
    """Voting started."""
    type: str = "voting_started"
    round_id: str
    options: List[VotingOptionSchema]
    ends_at: datetime
    duration_seconds: int


class WSVotingUpdate(WSMessageBase):
    """Vote counts updated."""
    type: str = "voting_update"
    votes: Dict[str, int]  # option_id -> count


class WSVotingEnded(WSMessageBase):
    """Voting ended."""
    type: str = "voting_ended"
    round_id: str
    winner: VotingOptionSchema
    results: List[VotingOptionSchema]


class WSProjectLiked(WSMessageBase):
    """Project was liked."""
    type: str = "project_liked"
    project_id: str
    like_count: int

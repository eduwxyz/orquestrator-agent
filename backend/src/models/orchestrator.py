"""Orchestrator database models for autonomous execution."""

import enum
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class GoalStatus(str, enum.Enum):
    """Status of a goal in the orchestrator."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ActionType(str, enum.Enum):
    """Types of actions the orchestrator can take."""
    VERIFY_LIMIT = "verify_limit"
    DECOMPOSE = "decompose"
    EXECUTE_CARD = "execute_card"
    CREATE_FIX = "create_fix"
    WAIT = "wait"
    COMPLETE_GOAL = "complete_goal"


class Goal(Base):
    """Goal model for orchestrator objectives."""

    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus),
        default=GoalStatus.PENDING,
        nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Decomposed cards (list of card IDs)
    cards: Mapped[List[str] | None] = mapped_column(JSON, nullable=True, default=list)

    # Learning extracted after completion
    learning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Qdrant learning ID if stored
    learning_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Error info if failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source info (e.g., chat session)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Metrics
    total_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)

    # Relationships
    actions: Mapped[List["OrchestratorAction"]] = relationship(
        "OrchestratorAction",
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="OrchestratorAction.started_at"
    )

    def __repr__(self) -> str:
        return f"<Goal(id={self.id}, status={self.status}, description={self.description[:30]}...)>"


class OrchestratorAction(Base):
    """Action model for orchestrator decisions and executions."""

    __tablename__ = "orchestrator_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False
    )

    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType),
        nullable=False
    )

    # Input context for the action
    input_context: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Output result from the action
    output_result: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Result
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Related card if action is EXECUTE_CARD or CREATE_FIX
    card_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationship
    goal: Mapped["Goal"] = relationship("Goal", back_populates="actions")

    def __repr__(self) -> str:
        return f"<OrchestratorAction(id={self.id}, type={self.action_type}, success={self.success})>"


class OrchestratorLogType(str, enum.Enum):
    """Types of orchestrator log entries."""
    READ = "read"
    QUERY = "query"
    THINK = "think"
    ACT = "act"
    RECORD = "record"
    LEARN = "learn"
    ERROR = "error"
    INFO = "info"


class OrchestratorLog(Base):
    """Log model for orchestrator loop execution."""

    __tablename__ = "orchestrator_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    log_type: Mapped[OrchestratorLogType] = mapped_column(
        Enum(OrchestratorLogType),
        nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Additional context as JSON
    context: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Related goal if any
    goal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # For cleanup - logs expire after retention period
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return f"<OrchestratorLog(id={self.id}, type={self.log_type}, content={self.content[:30]}...)>"

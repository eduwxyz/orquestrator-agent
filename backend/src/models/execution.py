"""Execution database models."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, Integer, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ExecutionStatus(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class Execution(Base):
    """Execution model for tracking card workflow executions."""

    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, native_enum=False, values_callable=lambda obj: [e.value for e in obj]),
        default=ExecutionStatus.IDLE
    )
    command: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # /plan, /implement, /test, /review
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # em segundos
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Campos para rastrear estágio do workflow
    workflow_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # plan, implement, test, review, completed
    workflow_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Campos para token tracking
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Campo para custo da execução
    execution_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)

    # Relacionamentos
    card = relationship("Card", back_populates="executions")
    logs: Mapped[List["ExecutionLog"]] = relationship(
        "ExecutionLog",
        back_populates="execution",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, card_id={self.card_id}, status={self.status})>"


class ExecutionLog(Base):
    """Log entries for execution progress."""

    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # info, error, warning, success, command, system
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sequence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relacionamento
    execution: Mapped["Execution"] = relationship("Execution", back_populates="logs")

    def __repr__(self) -> str:
        return f"<ExecutionLog(id={self.id}, type={self.type}, sequence={self.sequence})>"

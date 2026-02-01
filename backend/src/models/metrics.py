"""Modelos de métricas para análise de desempenho e custos."""

from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Date, Text, JSON, BigInteger, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ProjectMetrics(Base):
    """Métricas agregadas por projeto."""

    __tablename__ = "project_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("active_project.id", ondelete="CASCADE"),
        nullable=False
    )

    # Métricas de Tokens
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Métricas de Tempo
    avg_execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_execution_time_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Métricas de Custo
    total_cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    cost_by_model: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # {"opus-4.5": 12.50, "sonnet-4.5": 8.30}

    # Métricas de Produtividade
    cards_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cards_in_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Agregações Temporais
    metrics_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    metrics_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-23 para agregação por hora

    # Metadados
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "id": self.id,
            "projectId": self.project_id,
            "totalInputTokens": self.total_input_tokens,
            "totalOutputTokens": self.total_output_tokens,
            "totalTokens": self.total_tokens,
            "avgExecutionTimeMs": self.avg_execution_time_ms,
            "minExecutionTimeMs": self.min_execution_time_ms,
            "maxExecutionTimeMs": self.max_execution_time_ms,
            "totalExecutionTimeMs": self.total_execution_time_ms,
            "totalCostUsd": float(self.total_cost_usd) if self.total_cost_usd else 0,
            "costByModel": self.cost_by_model or {},
            "cardsCompleted": self.cards_completed,
            "cardsInProgress": self.cards_in_progress,
            "successRate": self.success_rate,
            "metricsDate": self.metrics_date.isoformat() if self.metrics_date else None,
            "metricsHour": self.metrics_hour,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ProjectMetrics(id={self.id}, project_id={self.project_id})>"


class ExecutionMetrics(Base):
    """Métricas detalhadas por execução."""

    __tablename__ = "execution_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    execution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False
    )
    card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("active_project.id", ondelete="CASCADE"),
        nullable=False
    )

    # Detalhes da Execução
    command: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # /plan, /implement, /test, /review
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Métricas de Tempo
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Métricas de Tokens
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Métricas de Custo
    estimated_cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)

    # Status
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # success, error, cancelled
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadados
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relacionamentos
    execution = relationship("Execution", foreign_keys=[execution_id])
    card = relationship("Card", foreign_keys=[card_id])

    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "id": self.id,
            "executionId": self.execution_id,
            "cardId": self.card_id,
            "projectId": self.project_id,
            "command": self.command,
            "modelUsed": self.model_used,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "durationMs": self.duration_ms,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "totalTokens": self.total_tokens,
            "estimatedCostUsd": float(self.estimated_cost_usd) if self.estimated_cost_usd else 0,
            "status": self.status,
            "errorMessage": self.error_message,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<ExecutionMetrics(id={self.id}, execution_id={self.execution_id})>"

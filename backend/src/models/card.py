"""Card database model."""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, JSON, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Dict, Any

from ..database import Base


class Card(Base):
    """Card model for Kanban board."""

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    column_id: Mapped[str] = mapped_column(String(20), nullable=False, default="backlog")
    spec_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_plan: Mapped[str] = mapped_column(String(20), default="opus-4.5", nullable=False)
    model_implement: Mapped[str] = mapped_column(String(20), default="opus-4.5", nullable=False)
    model_test: Mapped[str] = mapped_column(String(20), default="opus-4.5", nullable=False)
    model_review: Mapped[str] = mapped_column(String(20), default="opus-4.5", nullable=False)
    images: Mapped[List[Dict[str, Any]] | None] = mapped_column(JSON, nullable=True, default=list)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Novos campos para rastreamento de correções
    parent_card_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("cards.id", ondelete="SET NULL"),
        nullable=True
    )
    is_fix_card: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    test_error_context: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Campos para worktree isolation
    branch_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    worktree_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )
    base_branch: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # Campos para diff visualization
    diff_stats: Mapped[Dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True
    )

    # Relacionamento com execuções
    executions = relationship("Execution", back_populates="card", cascade="all, delete-orphan")

    # Relacionamento com activity logs
    activity_logs = relationship("ActivityLog", back_populates="card", cascade="all, delete-orphan")

    # Relacionamento auto-referencial
    parent_card = relationship("Card", back_populates="fix_cards", remote_side=[id])
    fix_cards = relationship("Card", back_populates="parent_card")

    def __repr__(self) -> str:
        return f"<Card(id={self.id}, title={self.title}, column={self.column_id})>"

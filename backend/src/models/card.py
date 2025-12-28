"""Card database model."""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Card(Base):
    """Card model for Kanban board."""

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    column_id: Mapped[str] = mapped_column(String(20), nullable=False, default="backlog")
    spec_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Card(id={self.id}, title={self.title}, column={self.column_id})>"

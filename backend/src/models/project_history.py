"""Project history model for tracking all loaded projects."""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Boolean, DateTime, Integer, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for project history database."""

    pass


class ProjectHistory(Base):
    """Model for storing project access history and favorites."""

    __tablename__ = "project_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # project hash
    path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    has_claude_config: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    first_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    access_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extra_metadata: Mapped[Optional[str]] = mapped_column(
        "metadata",
        Text,
        nullable=True
    )  # JSON with extra info

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "hasClaudeConfig": self.has_claude_config,
            "isFavorite": self.is_favorite,
            "lastAccessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "firstAccessed": self.first_accessed.isoformat() if self.first_accessed else None,
            "accessCount": self.access_count,
        }

    def __repr__(self) -> str:
        return f"<ProjectHistory(id={self.id}, name={self.name})>"

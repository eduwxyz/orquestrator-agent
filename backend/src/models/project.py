"""Active project model."""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ActiveProject(Base):
    """Modelo para armazenar o projeto atualmente ativo."""

    __tablename__ = "active_project"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    has_claude_config: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    claude_config_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converte o modelo para um dicionário."""
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "hasClaudeConfig": self.has_claude_config,
            "claudeConfigPath": self.claude_config_path,
            "loadedAt": self.loaded_at.isoformat() if self.loaded_at else None,
        }

    def __repr__(self) -> str:
        return f"<ActiveProject(id={self.id}, name={self.name})>"

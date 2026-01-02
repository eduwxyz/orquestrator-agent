from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from src.database import Base


class ActiveProject(Base):
    """Modelo para armazenar o projeto atualmente ativo."""

    __tablename__ = "active_project"

    id = Column(String, primary_key=True, index=True)
    path = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    has_claude_config = Column(Boolean, default=False)
    claude_config_path = Column(String, nullable=True)
    loaded_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        """Converte o modelo para um dicionário."""
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "hasClaudeConfig": self.has_claude_config,
            "claudeConfigPath": self.claude_config_path,
            "loadedAt": self.loaded_at.isoformat() if self.loaded_at else None,
        }
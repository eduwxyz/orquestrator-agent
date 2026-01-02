"""Project history model for tracking all loaded projects."""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for project history database."""

    pass


class ProjectHistory(Base):
    """Model for storing project access history and favorites."""

    __tablename__ = "project_history"

    id = Column(String, primary_key=True)  # project hash
    path = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    has_claude_config = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    first_accessed = Column(DateTime(timezone=True), server_default=func.now())
    access_count = Column(Integer, default=1)
    extra_metadata = Column("metadata", Text, nullable=True)  # JSON with extra info

    def to_dict(self):
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

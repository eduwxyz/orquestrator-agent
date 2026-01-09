"""Activity log database model."""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ActivityType(PyEnum):
    """Activity types for card operations."""
    CREATED = "created"
    MOVED = "moved"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    UPDATED = "updated"
    EXECUTED = "executed"
    COMMENTED = "commented"


class ActivityLog(Base):
    """Activity log model for tracking card changes."""

    __tablename__ = "activity_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    card_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType),
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Activity metadata
    from_column: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_column: Mapped[str | None] = mapped_column(String(20), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    card = relationship("Card", back_populates="activity_logs")

    def __repr__(self) -> str:
        return f"<ActivityLog(id={self.id}, card_id={self.card_id}, type={self.activity_type.value})>"

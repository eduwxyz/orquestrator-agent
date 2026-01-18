"""Models for Live Spectator System."""

from datetime import datetime
from enum import Enum
from sqlalchemy import Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from ..database import Base


class VoteType(str, Enum):
    """Types of votes."""
    PROJECT = "project"      # Vote for next project
    LIKE = "like"           # Like a completed project


class Vote(Base):
    """Vote model for spectator voting system."""

    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # What was voted for
    vote_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(255), nullable=False)  # project_id or option_id

    # Who voted (anonymous - by session/IP)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)  # IPv6 can be 45 chars

    # When
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # For voting rounds
    voting_round_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Vote(id={self.id}, type={self.vote_type}, target={self.target_id})>"


class VotingRound(Base):
    """Voting round model - represents a voting session."""

    __tablename__ = "voting_rounds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Winner
    winner_option_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    winner_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<VotingRound(id={self.id}, active={self.is_active})>"


class VotingOption(Base):
    """Voting option for a round."""

    __tablename__ = "voting_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Parent round
    voting_round_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("voting_rounds.id", ondelete="CASCADE"),
        nullable=False
    )

    # Option details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # game, app, site, etc.

    # Vote count (denormalized for performance)
    vote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<VotingOption(id={self.id}, title={self.title}, votes={self.vote_count})>"


class CompletedProject(Base):
    """Completed project for gallery."""

    __tablename__ = "completed_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Project info
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Media
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preview_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Stats
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Reference to original card
    card_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("cards.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    completed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<CompletedProject(id={self.id}, title={self.title}, likes={self.like_count})>"

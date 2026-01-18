"""Voting service for spectator voting system."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable, Awaitable, Tuple
from uuid import uuid4
import logging

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.live import Vote, VoteType, VotingRound, VotingOption
from ..schemas.live import VotingOptionSchema, VotingStateResponse

logger = logging.getLogger(__name__)

# Default voting options when no custom options provided
DEFAULT_VOTING_OPTIONS = [
    {"title": "Jogo", "category": "game", "description": "Criar um jogo interativo"},
    {"title": "Aplicativo", "category": "app", "description": "Desenvolver um aplicativo"},
    {"title": "Site", "category": "site", "description": "Criar um website"},
    {"title": "Ferramenta", "category": "tool", "description": "Desenvolver uma ferramenta/CLI"},
]


class VotingService:
    """Service to manage voting rounds."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Active round in memory for quick access
        self._active_round: Optional[VotingRound] = None
        self._active_options: List[VotingOption] = []

        # Timer task
        self._timer_task: Optional[asyncio.Task] = None

        # Callbacks
        self._on_started_callbacks: list[Callable[[VotingRound, List[VotingOption]], Awaitable[None]]] = []
        self._on_update_callbacks: list[Callable[[Dict[str, int]], Awaitable[None]]] = []
        self._on_ended_callbacks: list[Callable[[VotingOption, List[VotingOption]], Awaitable[None]]] = []

        # Sessions that voted in current round
        self._voted_sessions: set[str] = set()

        logger.info("VotingService initialized")

    @property
    def is_active(self) -> bool:
        """Check if voting is currently active."""
        if not self._active_round:
            return False
        return self._active_round.is_active and datetime.utcnow() < self._active_round.ends_at

    def get_state(self) -> VotingStateResponse:
        """Get current voting state."""
        if not self.is_active or not self._active_round:
            return VotingStateResponse(is_active=False)

        time_remaining = max(0, int((self._active_round.ends_at - datetime.utcnow()).total_seconds()))

        return VotingStateResponse(
            is_active=True,
            round_id=self._active_round.id,
            options=[
                VotingOptionSchema(
                    id=opt.id,
                    title=opt.title,
                    description=opt.description,
                    category=opt.category,
                    vote_count=opt.vote_count
                )
                for opt in self._active_options
            ],
            ends_at=self._active_round.ends_at,
            time_remaining_seconds=time_remaining
        )

    async def start_round(
        self,
        db: AsyncSession,
        duration_seconds: int = 300,
        options: Optional[List[Dict]] = None
    ) -> Tuple[VotingRound, List[VotingOption]]:
        """Start a new voting round."""
        if self.is_active:
            logger.warning("Voting round already active")
            return self._active_round, self._active_options

        # Create round
        round_id = str(uuid4())
        ends_at = datetime.utcnow() + timedelta(seconds=duration_seconds)

        voting_round = VotingRound(
            id=round_id,
            started_at=datetime.utcnow(),
            ends_at=ends_at,
            is_active=True
        )
        db.add(voting_round)

        # Create options
        option_list = options or DEFAULT_VOTING_OPTIONS
        voting_options = []

        for opt_data in option_list:
            option = VotingOption(
                id=str(uuid4()),
                voting_round_id=round_id,
                title=opt_data.get("title", "Option"),
                description=opt_data.get("description"),
                category=opt_data.get("category"),
                vote_count=0
            )
            db.add(option)
            voting_options.append(option)

        await db.commit()

        # Store in memory
        self._active_round = voting_round
        self._active_options = voting_options
        self._voted_sessions.clear()

        logger.info(f"Voting round started: {round_id}, ends at {ends_at}")

        # Notify callbacks
        for callback in self._on_started_callbacks:
            try:
                await callback(voting_round, voting_options)
            except Exception as e:
                logger.error(f"Error in voting started callback: {e}")

        # Start timer
        self._timer_task = asyncio.create_task(self._end_round_timer(db, duration_seconds))

        return voting_round, voting_options

    async def vote(
        self,
        db: AsyncSession,
        option_id: str,
        session_id: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """Cast a vote. Returns (success, message, new_count)."""
        if not self.is_active:
            return False, "Voting is not active", None

        # Check if already voted
        if session_id in self._voted_sessions:
            return False, "You have already voted in this round", None

        # Find option
        option = next((o for o in self._active_options if o.id == option_id), None)
        if not option:
            return False, "Invalid option", None

        # Create vote record
        vote = Vote(
            vote_type=VoteType.PROJECT,
            target_id=option_id,
            session_id=session_id,
            ip_address=ip_address,
            voting_round_id=self._active_round.id
        )
        db.add(vote)

        # Update option count
        option.vote_count += 1
        await db.execute(
            update(VotingOption)
            .where(VotingOption.id == option_id)
            .values(vote_count=option.vote_count)
        )

        await db.commit()

        # Mark as voted
        self._voted_sessions.add(session_id)

        logger.info(f"Vote recorded: {session_id[:8]}... -> {option.title} (now {option.vote_count})")

        # Notify callbacks with current counts
        votes_dict = {opt.id: opt.vote_count for opt in self._active_options}
        for callback in self._on_update_callbacks:
            try:
                await callback(votes_dict)
            except Exception as e:
                logger.error(f"Error in voting update callback: {e}")

        return True, "Vote recorded", option.vote_count

    async def _end_round_timer(self, db: AsyncSession, duration: int):
        """Timer to end the voting round."""
        try:
            await asyncio.sleep(duration)
            await self.end_round(db)
        except asyncio.CancelledError:
            logger.info("Voting timer cancelled")

    async def end_round(self, db: AsyncSession) -> Optional[VotingOption]:
        """End the current voting round and determine winner."""
        if not self._active_round:
            return None

        # Cancel timer if still running
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None

        # Find winner (highest votes)
        if self._active_options:
            winner = max(self._active_options, key=lambda o: o.vote_count)
        else:
            winner = None

        # Update round in DB
        self._active_round.is_active = False
        self._active_round.ended_at = datetime.utcnow()
        if winner:
            self._active_round.winner_option_id = winner.id
            self._active_round.winner_title = winner.title

        await db.execute(
            update(VotingRound)
            .where(VotingRound.id == self._active_round.id)
            .values(
                is_active=False,
                ended_at=self._active_round.ended_at,
                winner_option_id=self._active_round.winner_option_id,
                winner_title=self._active_round.winner_title
            )
        )
        await db.commit()

        logger.info(f"Voting round ended. Winner: {winner.title if winner else 'None'}")

        # Notify callbacks
        for callback in self._on_ended_callbacks:
            try:
                await callback(winner, self._active_options)
            except Exception as e:
                logger.error(f"Error in voting ended callback: {e}")

        # Clear memory
        round_copy = self._active_round
        options_copy = self._active_options.copy()
        self._active_round = None
        self._active_options = []
        self._voted_sessions.clear()

        return winner

    def on_started(self, callback: Callable[[VotingRound, List[VotingOption]], Awaitable[None]]) -> None:
        """Register callback for when voting starts."""
        self._on_started_callbacks.append(callback)

    def on_update(self, callback: Callable[[Dict[str, int]], Awaitable[None]]) -> None:
        """Register callback for vote count updates."""
        self._on_update_callbacks.append(callback)

    def on_ended(self, callback: Callable[[VotingOption, List[VotingOption]], Awaitable[None]]) -> None:
        """Register callback for when voting ends."""
        self._on_ended_callbacks.append(callback)


# Singleton instance
_voting_service = None


def get_voting_service() -> VotingService:
    """Get the singleton voting service."""
    global _voting_service
    if _voting_service is None:
        _voting_service = VotingService()
    return _voting_service

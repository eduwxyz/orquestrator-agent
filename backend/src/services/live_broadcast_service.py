"""Live broadcast service for aggregating and sending events to spectators."""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any, Set, List
from fastapi import WebSocket
import logging

from .presence_service import get_presence_service
from .voting_service import get_voting_service
from ..schemas.live import (
    WSPresenceUpdate, WSStatusUpdate, WSCardUpdate,
    WSLogEntry, WSVotingStarted, WSVotingUpdate, WSVotingEnded,
    WSProjectLiked, VotingOptionSchema
)

logger = logging.getLogger(__name__)


class LiveBroadcastService:
    """Service to broadcast events to live spectators."""

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

        # Active WebSocket connections
        self._connections: Dict[str, WebSocket] = {}

        # Current AI status
        self._current_status: Dict[str, Any] = {
            "is_working": False,
            "current_stage": None,
            "current_card": None,
            "progress": None
        }

        # Recent logs (keep last N for new connections)
        self._recent_logs: List[Dict[str, Any]] = []
        self._max_recent_logs = 50

        # Lock for thread safety
        self._lock = asyncio.Lock()

        # Setup callbacks from other services
        self._setup_callbacks()

        logger.info("LiveBroadcastService initialized")

    def _setup_callbacks(self):
        """Setup callbacks from presence and voting services."""
        presence = get_presence_service()
        voting = get_voting_service()

        # Presence changes
        presence.on_change(self._on_presence_change)

        # Voting events
        voting.on_started(self._on_voting_started)
        voting.on_update(self._on_voting_update)
        voting.on_ended(self._on_voting_ended)

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection."""
        async with self._lock:
            self._connections[session_id] = websocket
            logger.info(f"Live WS connected: {session_id[:8]}... Total: {len(self._connections)}")

        # Register with presence service
        presence = get_presence_service()
        await presence.connect(session_id)

        # Send initial state
        await self._send_initial_state(session_id, websocket)

    async def disconnect(self, session_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self._connections.pop(session_id, None)
            logger.info(f"Live WS disconnected: {session_id[:8]}... Total: {len(self._connections)}")

        # Unregister from presence service
        presence = get_presence_service()
        await presence.disconnect(session_id)

    async def _send_initial_state(self, session_id: str, websocket: WebSocket) -> None:
        """Send initial state to a new connection."""
        try:
            presence = get_presence_service()
            voting = get_voting_service()

            # Send presence count
            await self._send_to_one(websocket, WSPresenceUpdate(
                spectator_count=presence.count
            ))

            # Send current status
            await self._send_to_one(websocket, WSStatusUpdate(
                is_working=self._current_status["is_working"],
                current_stage=self._current_status.get("current_stage"),
                current_card=self._current_status.get("current_card"),
                progress=self._current_status.get("progress")
            ))

            # Send voting state if active
            if voting.is_active:
                state = voting.get_state()
                await self._send_to_one(websocket, WSVotingStarted(
                    round_id=state.round_id,
                    options=state.options,
                    ends_at=state.ends_at,
                    duration_seconds=state.time_remaining_seconds or 0
                ))

            # Send recent logs
            for log in self._recent_logs[-20:]:  # Last 20 logs
                await self._send_to_one(websocket, WSLogEntry(
                    content=log["content"],
                    log_type=log.get("log_type"),
                    timestamp=log.get("timestamp", datetime.utcnow())
                ))

        except Exception as e:
            logger.error(f"Error sending initial state: {e}")

    async def _send_to_one(self, websocket: WebSocket, message: Any) -> bool:
        """Send message to a single connection."""
        try:
            if hasattr(message, 'model_dump'):
                data = message.model_dump(mode='json')
            else:
                data = message
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
            return False

    async def broadcast(self, message: Any) -> int:
        """Broadcast message to all connected spectators."""
        if hasattr(message, 'model_dump'):
            data = message.model_dump(mode='json')
        else:
            data = message

        sent = 0
        failed = []

        async with self._lock:
            connections = list(self._connections.items())

        for session_id, ws in connections:
            try:
                await ws.send_json(data)
                sent += 1
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id[:8]}...: {e}")
                failed.append(session_id)

        # Cleanup failed connections
        for session_id in failed:
            await self.disconnect(session_id)

        return sent

    # =========================================================================
    # Status Updates
    # =========================================================================

    async def update_status(
        self,
        is_working: bool,
        current_stage: Optional[str] = None,
        current_card: Optional[Dict[str, Any]] = None,
        progress: Optional[int] = None
    ) -> None:
        """Update AI status and broadcast to spectators."""
        self._current_status = {
            "is_working": is_working,
            "current_stage": current_stage,
            "current_card": current_card,
            "progress": progress
        }

        await self.broadcast(WSStatusUpdate(
            is_working=is_working,
            current_stage=current_stage,
            current_card=current_card,
            progress=progress
        ))

    # =========================================================================
    # Card Updates
    # =========================================================================

    async def broadcast_card_moved(
        self,
        card: Dict[str, Any],
        from_column: str,
        to_column: str
    ) -> None:
        """Broadcast card movement to spectators."""
        from ..schemas.live import LiveCardResponse

        await self.broadcast(WSCardUpdate(
            action="moved",
            card=LiveCardResponse(
                id=card["id"],
                title=card["title"],
                description=card.get("description"),
                column_id=to_column,
                created_at=card.get("created_at", datetime.utcnow())
            ),
            from_column=from_column,
            to_column=to_column
        ))

    async def broadcast_card_created(self, card: Dict[str, Any]) -> None:
        """Broadcast new card to spectators."""
        from ..schemas.live import LiveCardResponse

        await self.broadcast(WSCardUpdate(
            action="created",
            card=LiveCardResponse(
                id=card["id"],
                title=card["title"],
                description=card.get("description"),
                column_id=card.get("column_id", "backlog"),
                created_at=card.get("created_at", datetime.utcnow())
            )
        ))

    # =========================================================================
    # Log Entries
    # =========================================================================

    async def broadcast_log(self, content: str, log_type: Optional[str] = None) -> None:
        """Broadcast log entry to spectators."""
        log_entry = {
            "content": content,
            "log_type": log_type,
            "timestamp": datetime.utcnow()
        }

        # Store in recent logs
        self._recent_logs.append(log_entry)
        if len(self._recent_logs) > self._max_recent_logs:
            self._recent_logs = self._recent_logs[-self._max_recent_logs:]

        await self.broadcast(WSLogEntry(
            content=content,
            log_type=log_type
        ))

    # =========================================================================
    # Presence Callbacks
    # =========================================================================

    async def _on_presence_change(self, count: int) -> None:
        """Handle presence count change."""
        await self.broadcast(WSPresenceUpdate(spectator_count=count))

    # =========================================================================
    # Voting Callbacks
    # =========================================================================

    async def _on_voting_started(self, round, options) -> None:
        """Handle voting started."""
        await self.broadcast(WSVotingStarted(
            round_id=round.id,
            options=[
                VotingOptionSchema(
                    id=opt.id,
                    title=opt.title,
                    description=opt.description,
                    category=opt.category,
                    vote_count=opt.vote_count
                )
                for opt in options
            ],
            ends_at=round.ends_at,
            duration_seconds=int((round.ends_at - datetime.utcnow()).total_seconds())
        ))

    async def _on_voting_update(self, votes: Dict[str, int]) -> None:
        """Handle vote count update."""
        await self.broadcast(WSVotingUpdate(votes=votes))

    async def _on_voting_ended(self, winner, all_options) -> None:
        """Handle voting ended."""
        if winner:
            winner_schema = VotingOptionSchema(
                id=winner.id,
                title=winner.title,
                description=winner.description,
                category=winner.category,
                vote_count=winner.vote_count
            )
        else:
            winner_schema = None

        await self.broadcast(WSVotingEnded(
            round_id="",  # Will be set properly
            winner=winner_schema,
            results=[
                VotingOptionSchema(
                    id=opt.id,
                    title=opt.title,
                    description=opt.description,
                    category=opt.category,
                    vote_count=opt.vote_count
                )
                for opt in sorted(all_options, key=lambda o: o.vote_count, reverse=True)
            ]
        ))

    # =========================================================================
    # Project Likes
    # =========================================================================

    async def broadcast_project_liked(self, project_id: str, like_count: int) -> None:
        """Broadcast project like to spectators."""
        await self.broadcast(WSProjectLiked(
            project_id=project_id,
            like_count=like_count
        ))

    # =========================================================================
    # Heartbeat handling
    # =========================================================================

    async def handle_ping(self, session_id: str) -> None:
        """Handle ping from client, update presence."""
        presence = get_presence_service()
        await presence.heartbeat(session_id)

        # Send pong
        async with self._lock:
            ws = self._connections.get(session_id)
            if ws:
                try:
                    await ws.send_json({"type": "pong"})
                except:
                    pass


# Singleton instance
_live_broadcast_service = None


def get_live_broadcast_service() -> LiveBroadcastService:
    """Get the singleton live broadcast service."""
    global _live_broadcast_service
    if _live_broadcast_service is None:
        _live_broadcast_service = LiveBroadcastService()
    return _live_broadcast_service

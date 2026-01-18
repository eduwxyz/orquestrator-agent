"""Presence service for tracking spectators."""

import asyncio
from datetime import datetime
from typing import Set, Dict, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)


class PresenceService:
    """Service to track online spectators."""

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

        # Active connections by session_id
        self._connections: Set[str] = set()

        # Callbacks for presence changes
        self._on_change_callbacks: list[Callable[[int], Awaitable[None]]] = []

        # Last activity tracking for cleanup
        self._last_activity: Dict[str, datetime] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info("PresenceService initialized")

    @property
    def count(self) -> int:
        """Get current spectator count."""
        return len(self._connections)

    async def connect(self, session_id: str) -> int:
        """Register a new spectator connection."""
        async with self._lock:
            if session_id not in self._connections:
                self._connections.add(session_id)
                self._last_activity[session_id] = datetime.utcnow()
                logger.info(f"Spectator connected: {session_id[:8]}... Total: {self.count}")

                # Notify callbacks
                await self._notify_change()

        return self.count

    async def disconnect(self, session_id: str) -> int:
        """Remove a spectator connection."""
        async with self._lock:
            if session_id in self._connections:
                self._connections.discard(session_id)
                self._last_activity.pop(session_id, None)
                logger.info(f"Spectator disconnected: {session_id[:8]}... Total: {self.count}")

                # Notify callbacks
                await self._notify_change()

        return self.count

    async def heartbeat(self, session_id: str) -> None:
        """Update last activity for a session."""
        async with self._lock:
            if session_id in self._connections:
                self._last_activity[session_id] = datetime.utcnow()

    def on_change(self, callback: Callable[[int], Awaitable[None]]) -> None:
        """Register callback for presence changes."""
        self._on_change_callbacks.append(callback)

    async def _notify_change(self) -> None:
        """Notify all callbacks about presence change."""
        count = self.count
        for callback in self._on_change_callbacks:
            try:
                await callback(count)
            except Exception as e:
                logger.error(f"Error in presence callback: {e}")

    async def cleanup_stale(self, timeout_seconds: int = 60) -> int:
        """Remove connections that haven't sent heartbeat."""
        now = datetime.utcnow()
        removed = 0

        async with self._lock:
            stale = [
                sid for sid, last in self._last_activity.items()
                if (now - last).total_seconds() > timeout_seconds
            ]

            for sid in stale:
                self._connections.discard(sid)
                self._last_activity.pop(sid, None)
                removed += 1

            if removed > 0:
                logger.info(f"Cleaned up {removed} stale connections. Total: {self.count}")
                await self._notify_change()

        return removed


# Singleton instance
_presence_service = None


def get_presence_service() -> PresenceService:
    """Get the singleton presence service."""
    global _presence_service
    if _presence_service is None:
        _presence_service = PresenceService()
    return _presence_service

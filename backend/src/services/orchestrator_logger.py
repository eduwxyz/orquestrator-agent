"""Orchestrator logger for file and WebSocket logging."""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorLogEntry:
    """A single log entry from the orchestrator."""
    timestamp: str
    level: str  # info, warning, error, debug
    step: str   # read, query, think, act, record, learn
    message: str
    goal_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class OrchestratorLogger:
    """
    Logger for orchestrator that writes to both file and WebSocket.

    Provides real-time updates to connected clients while maintaining
    a persistent log file.
    """

    def __init__(self, log_file: str = "orchestrator.log"):
        self.log_file = Path(log_file)
        self._websockets: List[WebSocket] = []
        self._buffer: List[OrchestratorLogEntry] = []
        self._max_buffer_size = 100

    # ==================== FILE LOGGING ====================

    def _write_to_file(self, entry: OrchestratorLogEntry) -> None:
        """Write a log entry to the file."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                line = json.dumps(asdict(entry), ensure_ascii=False)
                f.write(line + "\n")
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")

    def read_recent_logs(self, limit: int = 50) -> List[OrchestratorLogEntry]:
        """Read recent logs from the file."""
        entries = []
        try:
            if not self.log_file.exists():
                return entries

            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Get last N lines
            for line in lines[-limit:]:
                try:
                    data = json.loads(line.strip())
                    entries.append(OrchestratorLogEntry(**data))
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")

        return entries

    # ==================== WEBSOCKET MANAGEMENT ====================

    async def connect(self, websocket: WebSocket) -> None:
        """Add a WebSocket connection."""
        await websocket.accept()
        self._websockets.append(websocket)
        logger.info(f"[OrchestratorLogger] Client connected. Total: {len(self._websockets)}")

        # Send recent buffer to new client
        for entry in self._buffer[-20:]:
            try:
                await websocket.send_json(asdict(entry))
            except Exception:
                pass

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self._websockets:
            self._websockets.remove(websocket)
        logger.info(f"[OrchestratorLogger] Client disconnected. Total: {len(self._websockets)}")

    async def _broadcast(self, entry: OrchestratorLogEntry) -> None:
        """Broadcast a log entry to all connected WebSockets."""
        if not self._websockets:
            return

        disconnected = []
        for ws in self._websockets:
            try:
                await ws.send_json(asdict(entry))
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

    # ==================== LOGGING METHODS ====================

    async def log(
        self,
        step: str,
        message: str,
        level: str = "info",
        goal_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a message to file and broadcast to WebSockets.

        Args:
            step: The orchestrator step (read, query, think, act, record, learn)
            message: The log message
            level: Log level (info, warning, error, debug)
            goal_id: Optional goal ID this log relates to
            data: Optional additional data
        """
        entry = OrchestratorLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            step=step,
            message=message,
            goal_id=goal_id,
            data=data,
        )

        # Add to buffer
        self._buffer.append(entry)
        if len(self._buffer) > self._max_buffer_size:
            self._buffer = self._buffer[-self._max_buffer_size:]

        # Write to file
        self._write_to_file(entry)

        # Broadcast to WebSockets
        await self._broadcast(entry)

        # Also log to standard logger
        log_msg = f"[{step.upper()}] {message}"
        if level == "error":
            logger.error(log_msg)
        elif level == "warning":
            logger.warning(log_msg)
        elif level == "debug":
            logger.debug(log_msg)
        else:
            logger.info(log_msg)

    # Convenience methods for each step
    async def log_read(self, message: str, goal_id: Optional[str] = None, data: Optional[dict] = None):
        await self.log("read", message, "info", goal_id, data)

    async def log_query(self, message: str, goal_id: Optional[str] = None, data: Optional[dict] = None):
        await self.log("query", message, "info", goal_id, data)

    async def log_think(self, message: str, goal_id: Optional[str] = None, data: Optional[dict] = None):
        await self.log("think", message, "info", goal_id, data)

    async def log_act(self, message: str, goal_id: Optional[str] = None, data: Optional[dict] = None):
        await self.log("act", message, "info", goal_id, data)

    async def log_record(self, message: str, goal_id: Optional[str] = None, data: Optional[dict] = None):
        await self.log("record", message, "info", goal_id, data)

    async def log_learn(self, message: str, goal_id: Optional[str] = None, data: Optional[dict] = None):
        await self.log("learn", message, "info", goal_id, data)

    async def log_error(self, message: str, goal_id: Optional[str] = None, data: Optional[dict] = None):
        await self.log("error", message, "error", goal_id, data)

    async def log_info(self, message: str, goal_id: Optional[str] = None, data: Optional[dict] = None):
        await self.log("info", message, "info", goal_id, data)

    # ==================== STATUS ====================

    def get_status(self) -> Dict[str, Any]:
        """Get logger status."""
        return {
            "log_file": str(self.log_file),
            "connected_clients": len(self._websockets),
            "buffer_size": len(self._buffer),
        }


# Global instance
_orchestrator_logger: Optional[OrchestratorLogger] = None


def get_orchestrator_logger(log_file: str = "orchestrator.log") -> OrchestratorLogger:
    """Get or create the global orchestrator logger."""
    global _orchestrator_logger
    if _orchestrator_logger is None:
        _orchestrator_logger = OrchestratorLogger(log_file=log_file)
    return _orchestrator_logger

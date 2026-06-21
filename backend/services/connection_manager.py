"""
WebSocket Connection Manager — Task 4.2
========================================
Tracks all active WebSocket connections and provides
thread-safe broadcast to all or a subset of clients.
"""

import asyncio
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Singleton that manages every open WebSocket connection.

    Design notes:
    - Uses an asyncio.Lock so concurrent broadcast calls don't race.
    - Automatically removes dead connections on first failed send.
    - No Redis needed: works correctly for a single FastAPI process.
      If you ever scale to multiple workers, swap broadcast() to use
      Redis pub/sub (Phase 6 Task 6.2) without changing any callers.
    """

    def __init__(self):
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("WS client connected  | total=%d", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("WS client disconnected | total=%d", len(self._connections))

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to every connected client."""
        if not self._connections:
            return

        payload = json.dumps(message, default=str)
        dead: set[WebSocket] = set()

        # Snapshot under lock, then send outside lock to avoid blocking
        async with self._lock:
            snapshot = set(self._connections)

        for ws in snapshot:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                self._connections -= dead
            logger.debug("Removed %d dead WS connections", len(dead))

    @property
    def count(self) -> int:
        return len(self._connections)


# ── Singleton shared across the entire app ────────────────────────────────────
manager = ConnectionManager()

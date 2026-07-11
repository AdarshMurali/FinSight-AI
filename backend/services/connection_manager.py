"""
WebSocket Connection Manager — Task 4.2
========================================
Tracks all active WebSocket connections and provides
thread-safe broadcast to all or a subset of clients.
"""

import asyncio
import json
import logging
from typing import Optional
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
    - Task 6.4: each connection is authenticated at handshake time and tagged
      with the portfolios it's allowed to see (None = admin, unrestricted).
      broadcast(message, portfolio_id=...) filters accordingly; messages with
      no portfolio_id (connection confirmations, the Kafka news ticker) go to
      everyone, same as before.
    """

    def __init__(self):
        # value = None means unrestricted (admin); otherwise the set of
        # portfolio_ids this connection's manager is allowed to see.
        self._connections: dict[WebSocket, Optional[set[int]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, allowed_portfolio_ids: Optional[set[int]]) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[websocket] = allowed_portfolio_ids
        logger.info("WS client connected  | total=%d", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)
        logger.info("WS client disconnected | total=%d", len(self._connections))

    async def broadcast(self, message: dict, portfolio_id: Optional[int] = None) -> None:
        """Send a JSON message to connected clients. If portfolio_id is given,
        only clients whose allowed set includes it (or are unrestricted/admin)
        receive it — otherwise every connection gets the message."""
        if not self._connections:
            return

        payload = json.dumps(message, default=str)
        dead: set[WebSocket] = set()

        # Snapshot under lock, then send outside lock to avoid blocking
        async with self._lock:
            snapshot = dict(self._connections)

        for ws, allowed in snapshot.items():
            if portfolio_id is not None and allowed is not None and portfolio_id not in allowed:
                continue
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.pop(ws, None)
            logger.debug("Removed %d dead WS connections", len(dead))

    @property
    def count(self) -> int:
        return len(self._connections)


# ── Singleton shared across the entire app ────────────────────────────────────
manager = ConnectionManager()

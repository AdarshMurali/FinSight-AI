"""
Redis cache helper — Task 6.2
=============================
One reusable get_or_set() wrapper instead of scattering caching logic
per-endpoint. Falls back to computing fresh every time if Redis is
unreachable — same graceful-degradation posture as ChromaDB elsewhere
in this app (a cache outage should never take the API down with it).
"""
import json
import logging
from typing import Any, Callable, Optional

import redis

from config import settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None
_client_broken = False  # avoid retrying a connection on every single request once it's known down


def _get_client() -> Optional[redis.Redis]:
    global _client, _client_broken
    if _client_broken:
        return None
    if _client is None:
        _client = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT,
            decode_responses=True, socket_connect_timeout=1, socket_timeout=1,
        )
    return _client


def get_or_set(key: str, ttl: int, fetch_fn: Callable[[], Any]) -> Any:
    """Return the cached value for `key` if present, otherwise call fetch_fn(),
    cache its result for `ttl` seconds, and return it. fetch_fn's return value
    must be JSON-serializable."""
    client = _get_client()
    if client is not None:
        try:
            cached = client.get(key)
            if cached is not None:
                return json.loads(cached)
        except Exception:
            _mark_broken()
            client = None

    value = fetch_fn()

    if client is not None:
        try:
            client.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            _mark_broken()

    return value


def invalidate(*keys: str) -> None:
    """Best-effort delete — used after a write so the next read isn't served
    a stale cached value for the rest of its TTL."""
    client = _get_client()
    if client is None or not keys:
        return
    try:
        client.delete(*keys)
    except Exception:
        _mark_broken()


def _mark_broken() -> None:
    global _client_broken
    if not _client_broken:
        logger.warning("[Cache] Redis unavailable — falling back to uncached reads")
        _client_broken = True

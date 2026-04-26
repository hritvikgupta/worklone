"""Shared asyncio Redis client (singleton)."""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlsplit

import redis.asyncio as aioredis

from backend.core.dispatch.config import REDIS_URL

logger = logging.getLogger("dispatch.redis")

_client: Optional[aioredis.Redis] = None
_DEFAULT_REDIS_URL = "redis://localhost:6379/0"
_VALID_REDIS_SCHEMES = {"redis", "rediss", "unix"}


def _normalize_redis_url(raw_url: Optional[str]) -> str:
    """Normalize REDIS_URL and tolerate host:port style values."""
    candidate = (raw_url or "").strip()
    if not candidate:
        return _DEFAULT_REDIS_URL

    parsed = urlsplit(candidate)
    if parsed.scheme in _VALID_REDIS_SCHEMES:
        return candidate
    if parsed.scheme:
        logger.warning(
            "Invalid REDIS_URL scheme '%s'; falling back to %s",
            parsed.scheme,
            _DEFAULT_REDIS_URL,
        )
        return _DEFAULT_REDIS_URL

    # Allow shorthand like "localhost:6379/0" by prepending redis://
    return f"redis://{candidate}"


def get_redis() -> aioredis.Redis:
    """Return the process-wide async Redis client."""
    global _client
    if _client is None:
        redis_url = _normalize_redis_url(REDIS_URL)
        _client = aioredis.from_url(
            redis_url,
            decode_responses=True,
            encoding="utf-8",
            health_check_interval=30,
        )
        logger.info("Redis client initialized url=%s", redis_url)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:  # noqa: BLE001
            pass
        _client = None


async def ping() -> bool:
    try:
        return await get_redis().ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis ping failed: %s", exc)
        return False

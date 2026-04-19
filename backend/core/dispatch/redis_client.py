"""Shared asyncio Redis client (singleton)."""

from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis

from backend.core.dispatch.config import REDIS_URL

logger = logging.getLogger("dispatch.redis")

_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Return the process-wide async Redis client."""
    global _client
    if _client is None:
        _client = aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            encoding="utf-8",
            health_check_interval=30,
        )
        logger.info("Redis client initialized url=%s", REDIS_URL)
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

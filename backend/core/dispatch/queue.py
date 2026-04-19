"""Ready-queue helpers — the BullMQ-equivalent for this project.

Dispatcher LPUSHes admitted job ids into ceo:ready:{lane}. Workers BRPOP
from the list they own. One Redis list per lane keeps workers cache-hot on
the lane they specialize in, and lets us scale concurrency independently.
"""

from __future__ import annotations

import logging
from typing import Optional

from backend.core.dispatch.config import q_ready, q_waiting, k_user_waiting
from backend.core.dispatch.redis_client import get_redis

logger = logging.getLogger("dispatch.queue")


async def push_ready(job_id: str, lane: str) -> None:
    await get_redis().lpush(q_ready(lane), job_id)


async def pop_ready(lane: str, timeout: float = 5.0) -> Optional[str]:
    """Blocking pop — returns job_id or None if the timeout elapses."""
    r = get_redis()
    res = await r.brpop(q_ready(lane), timeout=timeout)
    if res is None:
        return None
    _, job_id = res
    return job_id


async def remove_from_waiting(job_id: str, lane: str, user_id: str) -> None:
    pipe = get_redis().pipeline()
    pipe.zrem(q_waiting(lane), job_id)
    pipe.srem(k_user_waiting(user_id), job_id)
    await pipe.execute()


async def list_waiting(lane: str, limit: int = 50) -> list[str]:
    return await get_redis().zrange(q_waiting(lane), 0, limit - 1)

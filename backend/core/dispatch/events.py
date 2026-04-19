"""
Pub/sub events — bridge between workers and the Socket.IO realtime server.

Any process can publish a JSON event to `ceo:events`. The socket.io server
subscribes once and re-broadcasts to browsers. This matches sim's
Socket.IO + Redis adapter pattern.

Event shape:
    {
      "type": "employee.status_changed" | "run.progress" | "run.completed" | ...,
      "employee_id"?: str,
      "run_id"?: str,
      "user_id"?: str,
      "status"?: str,
      "data"?: {...},
      "ts": float,
    }
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from backend.core.dispatch.config import K_EVENTS
from backend.core.dispatch.redis_client import get_redis

logger = logging.getLogger("dispatch.events")


async def publish_event(event_type: str, **fields: Any) -> None:
    """Fire-and-forget event broadcast. Never raises."""
    payload = {"type": event_type, "ts": time.time(), **fields}
    try:
        await get_redis().publish(K_EVENTS, json.dumps(payload, default=str))
    except Exception as exc:  # noqa: BLE001
        logger.warning("publish_event(%s) failed: %s", event_type, exc)


async def employee_status_changed(employee_id: str, status: str, *, run_id: str | None = None,
                                  kind: str | None = None, user_id: str | None = None) -> None:
    await publish_event(
        "employee.status_changed",
        employee_id=employee_id,
        status=status,
        run_id=run_id,
        kind=kind,
        user_id=user_id,
    )


async def run_progress(run_id: str, *, job_id: str | None = None, user_id: str | None = None,
                       phase: str | None = None, data: dict | None = None) -> None:
    await publish_event(
        "run.progress",
        run_id=run_id,
        job_id=job_id,
        user_id=user_id,
        phase=phase,
        data=data or {},
    )


async def run_completed(run_id: str, *, job_id: str | None = None, user_id: str | None = None,
                        status: str = "completed", error: str | None = None) -> None:
    await publish_event(
        "run.completed",
        run_id=run_id,
        job_id=job_id,
        user_id=user_id,
        status=status,
        error=error,
    )

"""
Socket.IO server — mounts onto the FastAPI ASGI app at /socket.io.

Two flows:
  - INBOUND (browser → server): clients connect and optionally `emit("subscribe",
    {employee_ids: [...], run_ids: [...]})` to join rooms. We use rooms so we
    can target broadcasts per-employee / per-run without spamming everyone.
  - OUTBOUND (Redis pub/sub → browser): a single subscriber task listens on
    `ceo:events` and rebroadcasts each message to the appropriate rooms.

This exactly mirrors sim's Socket.IO + Redis adapter pattern, adapted to
Python. We do NOT use python-socketio's built-in Redis manager (AsyncRedisManager)
because we already have our own event channel — using our own subscriber gives
us one-source-of-truth for event shape.
"""

from __future__ import annotations

import asyncio
import json
import logging

import socketio

from backend.core.dispatch.config import K_EVENTS
from backend.core.dispatch.redis_client import get_redis

logger = logging.getLogger("realtime.socket")


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # tightened by the outer FastAPI CORS; socket.io layers its own
    logger=False,
    engineio_logger=False,
)


# The FastAPI app mounts us at /socket.io, and Starlette strips that prefix
# before delegating to this ASGI app. So we set socketio_path="" and the
# final URL the browser hits is simply /socket.io/ (same as socket.io default).
asgi_app = socketio.ASGIApp(sio, socketio_path="")


@sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> None:
    logger.debug("socket connect sid=%s auth=%s", sid, auth)
    # Every client lands in a global "all" room for coarse broadcasts.
    await sio.enter_room(sid, "all")
    # If the client provided a user_id in auth, join their user room so we
    # can target user-scoped events cheaply.
    user_id = (auth or {}).get("user_id") if isinstance(auth, dict) else None
    if user_id:
        await sio.enter_room(sid, f"user:{user_id}")


@sio.event
async def disconnect(sid: str) -> None:
    logger.debug("socket disconnect sid=%s", sid)


@sio.on("subscribe")
async def on_subscribe(sid: str, data: dict | None) -> None:
    """Client opts in to per-employee / per-run rooms.

    data: {"employee_ids": [...], "run_ids": [...]}
    """
    data = data or {}
    for eid in data.get("employee_ids") or []:
        await sio.enter_room(sid, f"emp:{eid}")
    for rid in data.get("run_ids") or []:
        await sio.enter_room(sid, f"run:{rid}")


@sio.on("unsubscribe")
async def on_unsubscribe(sid: str, data: dict | None) -> None:
    data = data or {}
    for eid in data.get("employee_ids") or []:
        await sio.leave_room(sid, f"emp:{eid}")
    for rid in data.get("run_ids") or []:
        await sio.leave_room(sid, f"run:{rid}")


# ─── Redis → Socket.IO bridge ────────────────────────────────────────────────

_bridge_task: asyncio.Task | None = None


async def _redis_bridge() -> None:
    """Subscribe to the dispatch event channel and rebroadcast to rooms."""
    r = get_redis()
    while True:
        try:
            pubsub = r.pubsub()
            await pubsub.subscribe(K_EVENTS)
            logger.info("socket bridge subscribed to %s", K_EVENTS)
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                raw = message.get("data")
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue
                await _dispatch(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("socket bridge error: %s", exc)
            await asyncio.sleep(1.0)


async def _dispatch(event: dict) -> None:
    event_type = event.get("type") or "event"
    rooms: list[str] = ["all"]

    emp_id = event.get("employee_id")
    run_id = event.get("run_id")
    user_id = event.get("user_id")

    if emp_id:
        rooms.append(f"emp:{emp_id}")
    if run_id:
        rooms.append(f"run:{run_id}")
    if user_id:
        rooms.append(f"user:{user_id}")

    # Emit to each room (de-dup via set just in case).
    seen: set[str] = set()
    for room in rooms:
        if room in seen:
            continue
        seen.add(room)
        try:
            await sio.emit(event_type, event, room=room)
        except Exception as exc:  # noqa: BLE001
            logger.warning("emit(%s, room=%s) failed: %s", event_type, room, exc)


async def start_bridge() -> None:
    global _bridge_task
    if _bridge_task and not _bridge_task.done():
        return
    _bridge_task = asyncio.create_task(_redis_bridge(), name="socket_redis_bridge")


async def stop_bridge() -> None:
    global _bridge_task
    if _bridge_task:
        _bridge_task.cancel()
        try:
            await _bridge_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        _bridge_task = None

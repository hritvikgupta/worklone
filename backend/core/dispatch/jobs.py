"""
Dispatch jobs — the admission-layer record representing one run.

A job has:
  - kind: "chat" | "sprint" | "team" | "workflow"
  - lane: usually == kind (chat lane has chat jobs, etc.)
  - required_employee_ids: list of employee ids whose leases must be free
  - payload: kind-specific inputs the worker needs to execute
  - status: waiting -> admitting -> running -> completed|failed|cancelled

Jobs live in two Redis structures:
  - ceo:job:{id}        — hash containing the serialized job (source of truth)
  - ceo:waiting:{lane}  — ZSET of job_ids sorted by created_at (dispatcher scan)
  - ceo:user:waiting:{user_id} — SET used for per-user queue-depth caps

When dispatcher admits the job it moves it out of waiting and pushes the id into
ceo:ready:{lane} for a worker to pop.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from backend.core.dispatch.config import (
    GLOBAL_QUEUE_DEPTH,
    USER_QUEUE_DEPTH,
    k_job,
    k_user_waiting,
    q_waiting,
)
from backend.core.dispatch.redis_client import get_redis

logger = logging.getLogger("dispatch.jobs")


STATUS_WAITING = "waiting"
STATUS_ADMITTING = "admitting"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"


@dataclass
class DispatchJob:
    id: str
    kind: str                          # chat | sprint | team | workflow
    lane: str
    user_id: str
    owner_id: str
    required_employee_ids: list[str]   # leases required to run
    payload: dict[str, Any]            # kind-specific inputs
    status: str = STATUS_WAITING
    created_at: float = field(default_factory=lambda: time.time())
    admitted_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    run_id: Optional[str] = None       # populated by worker (TeamRun id / SprintRun id / etc.)
    result: Optional[dict] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> "DispatchJob":
        data = json.loads(raw)
        return cls(**data)


def new_job_id(kind: str) -> str:
    return f"dj_{kind}_{uuid.uuid4().hex[:12]}"


class QueueFullError(Exception):
    pass


async def enqueue_job(
    *,
    kind: str,
    lane: str,
    user_id: str,
    owner_id: str,
    required_employee_ids: list[str],
    payload: dict[str, Any],
) -> DispatchJob:
    """Persist a new job and add it to the waiting queue.

    Raises QueueFullError if global or per-user caps are exceeded.
    Returns the created DispatchJob (with id set).
    """
    r = get_redis()

    # Queue depth checks (cheap — SCARD + sum of waiting zsets is overkill here,
    # so we use the user-waiting SET cardinality plus a rough global count).
    user_waiting = await r.scard(k_user_waiting(user_id))
    if user_waiting >= USER_QUEUE_DEPTH:
        raise QueueFullError(f"user queue full ({user_waiting}/{USER_QUEUE_DEPTH})")

    # Cheap global approximation: sum ZCARD of lane-waiting sets.
    global_total = 0
    for ln in ("chat", "sprint", "team", "workflow"):
        global_total += await r.zcard(q_waiting(ln))
    if global_total >= GLOBAL_QUEUE_DEPTH:
        raise QueueFullError(f"global queue full ({global_total}/{GLOBAL_QUEUE_DEPTH})")

    job = DispatchJob(
        id=new_job_id(kind),
        kind=kind,
        lane=lane,
        user_id=user_id or "",
        owner_id=owner_id or "",
        required_employee_ids=list(required_employee_ids or []),
        payload=payload or {},
    )

    pipe = r.pipeline()
    pipe.set(k_job(job.id), job.to_json())
    pipe.zadd(q_waiting(job.lane), {job.id: job.created_at})
    pipe.sadd(k_user_waiting(user_id), job.id)
    await pipe.execute()

    logger.info(
        "enqueued job=%s kind=%s lane=%s user=%s emps=%s",
        job.id, job.kind, job.lane, user_id, required_employee_ids,
    )
    return job


async def load_job(job_id: str) -> Optional[DispatchJob]:
    raw = await get_redis().get(k_job(job_id))
    if not raw:
        return None
    try:
        return DispatchJob.from_json(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("corrupt job record %s: %s", job_id, exc)
        return None


async def save_job(job: DispatchJob) -> None:
    await get_redis().set(k_job(job.id), job.to_json())


async def update_job_status(
    job_id: str,
    status: str,
    *,
    error: Optional[str] = None,
    run_id: Optional[str] = None,
    result: Optional[dict] = None,
) -> Optional[DispatchJob]:
    job = await load_job(job_id)
    if not job:
        return None
    job.status = status
    now = time.time()
    if status == STATUS_ADMITTING:
        job.admitted_at = now
    elif status == STATUS_RUNNING and not job.started_at:
        job.started_at = now
    elif status in (STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED):
        job.completed_at = now
    if error is not None:
        job.error = error
    if run_id is not None:
        job.run_id = run_id
    if result is not None:
        job.result = result
    await save_job(job)
    return job

"""
Dispatcher loop — Layer 2 admission control.

Every DISPATCHER_POLL_MS (default 250ms) the dispatcher:
  1. Walks lanes in priority order (chat > sprint > team > workflow).
  2. For each lane, scans the oldest N waiting jobs.
  3. For each job, attempts atomic `acquire_all` on its required employees
     (respecting per-user concurrency cap). Lua script handles the mutex.
  4. On success: removes the job from the waiting set, LPUSHes to the ready
     queue, marks job status=admitting, publishes `employee.status_changed`
     for each leased employee.
  5. On "busy" failure: leaves job in waiting (will retry next tick).
  6. On "user over cap" failure: stops scanning this user's jobs for this tick.

Starvation control: within a lane we order by `created_at` (FIFO). Across
lanes, higher-priority lanes always scan first, but because leases are
per-employee mutexes, a stuck chat job CAN'T block an unrelated team job.

Only ONE dispatcher should run per deployment (Redis is the shared state).
In production you'd run it as a single replica; for dev it starts inside the
FastAPI app at startup.
"""

from __future__ import annotations

import asyncio
import logging

from backend.core.dispatch.config import (
    DEFAULT_USER_CONCURRENCY,
    DISPATCHER_POLL_MS,
    DISPATCHER_SCAN_BATCH,
    LANES,
    LEASE_TTL_SECONDS,
)
from backend.core.dispatch.events import employee_status_changed, publish_event
from backend.core.dispatch.jobs import (
    STATUS_ADMITTING,
    load_job,
    update_job_status,
)
from backend.core.dispatch.leases import acquire_all
from backend.core.dispatch.queue import list_waiting, push_ready, remove_from_waiting

logger = logging.getLogger("dispatch.dispatcher")


class Dispatcher:
    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="dispatcher_loop")
        logger.info("dispatcher started poll=%dms", DISPATCHER_POLL_MS)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        logger.info("dispatcher stopped")

    async def _run_loop(self) -> None:
        delay = DISPATCHER_POLL_MS / 1000.0
        while self._running:
            try:
                await self._tick()
            except Exception as exc:  # noqa: BLE001
                logger.exception("dispatcher tick failed: %s", exc)
            await asyncio.sleep(delay)

    async def _tick(self) -> None:
        users_saturated: set[str] = set()
        for lane in LANES:
            candidates = await list_waiting(lane, DISPATCHER_SCAN_BATCH)
            for job_id in candidates:
                job = await load_job(job_id)
                if not job:
                    # Orphan id — drop.
                    await remove_from_waiting(job_id, lane, "")
                    continue
                if job.user_id in users_saturated:
                    continue
                if job.status != "waiting":
                    # Already admitted (left in waiting by accident) — clean up.
                    await remove_from_waiting(job_id, lane, job.user_id)
                    continue

                res = await acquire_all(
                    job_id=job.id,
                    user_id=job.user_id,
                    employee_ids=job.required_employee_ids,
                    user_cap=DEFAULT_USER_CONCURRENCY,
                    ttl_seconds=LEASE_TTL_SECONDS,
                )
                if res == 1:
                    await self._admit(job)
                elif res == -1:
                    # User at concurrency cap — skip all their remaining jobs this tick.
                    users_saturated.add(job.user_id)
                # res == 0 → at least one employee busy, leave in waiting.

    async def _admit(self, job) -> None:
        await remove_from_waiting(job.id, job.lane, job.user_id)
        await update_job_status(job.id, STATUS_ADMITTING)
        await push_ready(job.id, job.lane)
        logger.info("admitted job=%s kind=%s emps=%s", job.id, job.kind, job.required_employee_ids)
        # Emit busy event for each leased employee so the UI lights up immediately,
        # without waiting for the worker to pick the job up.
        for emp_id in job.required_employee_ids:
            await employee_status_changed(
                emp_id, "working", run_id=job.run_id, kind=job.kind, user_id=job.user_id,
            )
        await publish_event(
            "job.admitted",
            job_id=job.id,
            kind=job.kind,
            lane=job.lane,
            user_id=job.user_id,
            employee_ids=job.required_employee_ids,
        )

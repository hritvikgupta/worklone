"""
Worker entrypoint — pulls ready jobs, runs them, heartbeats leases.

Run as a standalone process:

    python -m backend.worker.main

Or programmatically via `WorkerPool.start()` from the FastAPI app (dev mode).

Each lane spawns its own pool of N concurrent BRPOP loops. When a job id
arrives, we:
  1. Load the DispatchJob from Redis.
  2. Mark status=running, emit run.progress.
  3. Start a heartbeat task (EXPIRE lease every LEASE_HEARTBEAT_SECONDS).
  4. Call the kind-specific executor.
  5. On finish/error: release employee leases, publish employee.status_changed
     and run.completed, mark the job completed/failed.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from backend.core.dispatch.config import (
    LANES,
    LEASE_HEARTBEAT_SECONDS,
    WORKER_CONCURRENCY_PER_LANE,
)
from backend.core.dispatch.events import (
    employee_status_changed,
    run_completed,
    run_progress,
)
from backend.core.dispatch.jobs import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    load_job,
    update_job_status,
)
from backend.core.dispatch.leases import heartbeat, release_all
from backend.core.dispatch.queue import pop_ready
from backend.worker.executor import execute

logger = logging.getLogger("worker.main")


class WorkerPool:
    def __init__(self, lanes: list[str] | None = None,
                 concurrency: dict[str, int] | None = None) -> None:
        self.lanes = lanes or list(LANES)
        # Chat doesn't go through the worker — chat is served inline by the
        # API so tokens can SSE-stream back to the user. Strip it.
        self.lanes = [ln for ln in self.lanes if ln != "chat"]
        self.concurrency = concurrency or WORKER_CONCURRENCY_PER_LANE
        self._tasks: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        for lane in self.lanes:
            n = max(1, int(self.concurrency.get(lane, 5)))
            for i in range(n):
                task = asyncio.create_task(self._consumer(lane, i), name=f"worker_{lane}_{i}")
                self._tasks.append(task)
        logger.info("worker pool started lanes=%s concurrency=%s", self.lanes,
                    {ln: self.concurrency.get(ln) for ln in self.lanes})

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        logger.info("worker pool stopped")

    async def _consumer(self, lane: str, slot: int) -> None:
        logger.debug("consumer lane=%s slot=%d start", lane, slot)
        while self._running:
            try:
                job_id = await pop_ready(lane, timeout=5.0)
            except Exception as exc:  # noqa: BLE001
                logger.warning("pop_ready(%s) failed: %s", lane, exc)
                await asyncio.sleep(1.0)
                continue
            if not job_id:
                continue
            try:
                await self._process(job_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("processing job %s failed: %s", job_id, exc)

    async def _process(self, job_id: str) -> None:
        job = await load_job(job_id)
        if not job:
            logger.warning("job %s missing from Redis; skipping", job_id)
            return

        logger.info("picked up job=%s kind=%s emps=%s", job.id, job.kind, job.required_employee_ids)
        await update_job_status(job.id, STATUS_RUNNING)
        await run_progress(job.run_id or job.id, job_id=job.id, user_id=job.user_id, phase="started")

        heartbeat_task = asyncio.create_task(self._heartbeat_loop(job.id, job.user_id))

        error: str | None = None
        result: dict | None = None
        try:
            result = await execute(job)
        except Exception as exc:  # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"
            logger.exception("job %s execution failed: %s", job.id, error)
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            # Release all employee leases and emit idle events.
            released = list(job.required_employee_ids)
            await release_all(job.id, job.user_id)
            for emp_id in released:
                await employee_status_changed(
                    emp_id, "idle", run_id=job.run_id, kind=job.kind, user_id=job.user_id,
                )
            final_status = STATUS_FAILED if error else STATUS_COMPLETED
            await update_job_status(job.id, final_status, error=error,
                                    run_id=job.run_id, result=result)
            await run_completed(
                job.run_id or job.id,
                job_id=job.id,
                user_id=job.user_id,
                status=final_status,
                error=error,
            )

    async def _heartbeat_loop(self, job_id: str, user_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(LEASE_HEARTBEAT_SECONDS)
                await heartbeat(job_id, user_id)
        except asyncio.CancelledError:
            return


# ─── Standalone entrypoint ───────────────────────────────────────────────────

async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    pool = WorkerPool()
    await pool.start()

    stop_event = asyncio.Event()

    def _handle_signal(*_: object) -> None:
        stop_event.set()

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _handle_signal)
            except NotImplementedError:
                pass  # windows
        await stop_event.wait()
    finally:
        await pool.stop()


if __name__ == "__main__":
    asyncio.run(_main())

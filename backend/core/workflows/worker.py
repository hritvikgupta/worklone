"""
Background Worker — executes scheduled workflows via DAG executor.

Simple polling loop:
- Finds workflows triggered by schedule
- Executes via WorkflowExecutor (deterministic DAG traversal)
- Handles pause/resume for human-in-the-loop blocks
- Processes pending resume requests
"""

import asyncio
from datetime import datetime, timedelta

from backend.db.stores.workflow_store import WorkflowStore
from backend.core.workflows.schedules.normalize import next_run_from_cron, normalize_schedule_config
from backend.core.workflows.engine.executor import WorkflowExecutor
from backend.core.logging import get_logger
from backend.core.dispatch.jobs import enqueue_job, QueueFullError

logger = get_logger("worker")


class BackgroundWorker:
    """
    Background job processor.

    Polls for scheduled workflows and pending resumes,
    executes via the deterministic DAG executor.
    """

    def __init__(
        self,
        store: WorkflowStore,
        poll_interval: float = 5.0,
        max_concurrent: int = 10,
    ):
        self.store = store
        self.executor = WorkflowExecutor(store)
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent
        self.running = False
        self._tasks: list[asyncio.Task] = []
        self._active_workflow_ids: set[str] = set()

    async def start(self):
        """Start the worker loop."""
        self.running = True
        logger.info(f"Worker started (poll={self.poll_interval}s, concurrency={self.max_concurrent})")

        while self.running:
            try:
                await self._process_tick()
            except Exception as e:
                logger.exception(f"Worker tick error: {e}")

            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """Stop the worker."""
        self.running = False
        for task in self._tasks:
            task.cancel()
        logger.info("Worker stopped")

    async def _process_tick(self):
        """Find scheduled workflows and pending resumes to process."""
        # 1. Process scheduled workflows
        scheduled = self.store.get_scheduled_workflows()
        if scheduled:
            logger.info(f"Found {len(scheduled)} scheduled workflows to execute")
            for workflow in scheduled[:self.max_concurrent]:
                workflow_id = workflow.get("id")
                if not workflow_id or workflow_id in self._active_workflow_ids:
                    continue
                self._active_workflow_ids.add(workflow_id)
                task = asyncio.create_task(self._execute_workflow(workflow))
                self._tasks.append(task)

        # Clean up finished tasks
        self._tasks = [t for t in self._tasks if not t.done()]

    async def _execute_workflow(self, workflow: dict):
        """Enqueue the workflow into the dispatch layer. The dispatcher admits
        it (respecting per-user concurrency) and the worker pool actually runs
        the DAG via WorkflowExecutor — no more inline execution in this process.
        """
        workflow_id = workflow["id"]
        workflow_name = workflow.get("name", workflow_id)
        owner_id = workflow.get("owner_id", "")

        try:
            # Advance next_run_at so we don't re-enqueue the same schedule tick.
            workflow_def = self.store.get_workflow(workflow_id, owner_id or None)
            if workflow_def:
                now = datetime.now()
                for trigger in workflow_def.triggers:
                    if trigger.trigger_type.value != "schedule" or not trigger.enabled:
                        continue
                    normalized_config = normalize_schedule_config(trigger.config)
                    cron_expression = trigger.cron_expression or normalized_config.get("cron", "")
                    next_run = next_run_from_cron(cron_expression) if cron_expression else now + timedelta(minutes=5)
                    self.store.update_schedule(trigger.id, now, next_run)

            await enqueue_job(
                kind="workflow",
                lane="workflow",
                user_id=owner_id or "anonymous",
                owner_id=owner_id,
                required_employee_ids=[],  # Harry is shared; concurrency cap gates us
                payload={"workflow_id": workflow_id, "trigger_type": "schedule"},
            )
            logger.info(f"[Worker] Enqueued workflow: {workflow_name} ({workflow_id})")

        except QueueFullError as e:
            logger.warning(f"[Worker] Queue full, deferring workflow {workflow_id}: {e}")
        except Exception as e:
            logger.exception(f"[Worker] Failed to enqueue workflow {workflow_id}: {e}")
        finally:
            self._active_workflow_ids.discard(workflow_id)

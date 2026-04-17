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
        """Execute a workflow via the DAG executor."""
        workflow_id = workflow["id"]
        workflow_name = workflow.get("name", workflow_id)
        owner_id = workflow.get("owner_id", "")

        logger.info(f"[Worker] Starting workflow: {workflow_name} ({workflow_id})")

        try:
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

            self.store.update_workflow_status(workflow_id, "running")

            result = await self.executor.execute_workflow(
                workflow_id=workflow_id,
                owner_id=owner_id,
                trigger_type="schedule",
            )

            if result.status.value == "paused":
                logger.info(f"[Worker] Workflow paused (human approval needed): {workflow_name}")
            elif result.status.value == "completed":
                self.store.update_workflow_status(workflow_id, "active")
                logger.info(f"[Worker] Completed workflow: {workflow_name}")
            else:
                self.store.update_workflow_status(workflow_id, "active")
                logger.warning(f"[Worker] Workflow {workflow_name} ended with status: {result.status.value}")

        except Exception as e:
            logger.exception(f"[Worker] Failed to execute workflow {workflow_id}: {e}")
            try:
                self.store.update_workflow_status(workflow_id, "failed", error=str(e))
            except Exception:
                pass
        finally:
            self._active_workflow_ids.discard(workflow_id)

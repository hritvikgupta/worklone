"""
Background Worker — wakes up the Executor Agent to execute scheduled workflows.

Simple polling loop:
- Finds workflows triggered by schedule
- Calls the CoWorkerAgent (Harry) to execute them
- No hardcoded DAG logic — the ReAct agent figures it out
"""

import asyncio
from datetime import datetime

from backend.workflows.store import WorkflowStore
from backend.workflows.coworker import create_coworker_agent
from backend.workflows.logger import get_logger

logger = get_logger("worker")


class BackgroundWorker:
    """
    Simple background job processor.

    Polls for scheduled workflows → wakes up the CoWorkerAgent (Harry) to execute them.
    """

    def __init__(
        self,
        store: WorkflowStore,
        poll_interval: float = 5.0,
        max_concurrent: int = 10,
    ):
        self.store = store
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent
        self.running = False
        self._tasks: list[asyncio.Task] = []

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
        """Find scheduled workflows and wake up the Executor Agent to run them."""
        scheduled = self.store.get_scheduled_workflows()

        if not scheduled:
            return

        logger.info(f"Found {len(scheduled)} scheduled workflows to execute")

        for workflow in scheduled[:self.max_concurrent]:
            task = asyncio.create_task(self._execute_workflow(workflow))
            self._tasks.append(task)

        # Clean up finished tasks
        self._tasks = [t for t in self._tasks if not t.done()]

    async def _execute_workflow(self, workflow: dict):
        """Wake up the Executor Agent to execute a workflow."""
        workflow_id = workflow["id"]
        workflow_name = workflow.get("name", workflow_id)
        user_id = workflow.get("user_id", "anonymous")

        logger.info(f"[Worker] Starting workflow: {workflow_name} ({workflow_id})")

        try:
            # Mark as running
            self.store.update_workflow_status(workflow_id, "running")

            # Wake up the Executor Agent
            agent = create_coworker_agent(user_id=user_id)
            
            # Execute the workflow via the agent's ReAct loop
            async for chunk in agent.execute_workflow(workflow_id, stream=False):
                pass  # Agent handles execution internally

            # Mark as completed
            self.store.update_workflow_status(workflow_id, "completed")
            logger.info(f"[Worker] Completed workflow: {workflow_name}")

        except Exception as e:
            logger.exception(f"[Worker] Failed to execute workflow {workflow_id}: {e}")
            try:
                self.store.update_workflow_status(workflow_id, "failed", error=str(e))
            except Exception:
                pass

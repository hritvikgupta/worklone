
"""
Agentic Workflow Executor.

This replaces the old DAG executor. It spawns a Coworker agent 
(with access to all tools) that iterates through the sequential tasks 
of a workflow, completing them one by one.
"""

import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from backend.core.workflows.types import Workflow, WorkflowStatus, ExecutionResult, WorkflowTaskStatus
from backend.db.stores.workflow_store import WorkflowStore
from backend.core.logging import get_logger
from backend.core.workflows.utils import generate_id

logger = get_logger("agentic_executor")

class WorkflowExecutor:
    """
    Executes a workflow by handing its tasks to an autonomous agent.
    """
    
    def __init__(self, store: Optional[WorkflowStore] = None):
        self.store = store or WorkflowStore()
        
    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_type: str = "manual",
        trigger_input: dict = None,
        owner_id: str = "",
        is_background: bool = True,
    ) -> ExecutionResult:
        """
        Start executing a workflow.
        """
        workflow = self.store.get_workflow(workflow_id, owner_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found.")

        # Clean up any stale RUNNING executions for this workflow
        self._cleanup_stale_executions(workflow_id, owner_id)

        execution_id = generate_id("exec")
        logger.info(f"Starting agentic execution {execution_id} for workflow {workflow_id}")
        
        result = ExecutionResult(
            execution_id=execution_id,
            workflow_id=workflow_id,
            owner_id=owner_id,
            status=WorkflowStatus.RUNNING,
            trigger_type=trigger_type,
            trigger_input=trigger_input or {},
            started_at=datetime.now(),
        )
        self.store.save_execution(result)
        self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING.value)
        
        if is_background:
            asyncio.create_task(self._run_agentic_loop(workflow, result))
        else:
            await self._run_agentic_loop(workflow, result)
            
        return result

    async def _run_agentic_loop(self, workflow: Workflow, result: ExecutionResult):
        """
        The actual agentic execution loop using CoWorkerAgent.
        """
        from backend.core.workflows.engine.coworker import CoWorkerAgent
        
        agent = CoWorkerAgent(owner_id=workflow.owner_id)
        
        success = True
        try:
            # execute_workflow is an AsyncGenerator. We consume it to let it run.
            async for event in agent.execute_workflow(workflow.id, trigger_input=result.trigger_input, stream=True, emit_events=True):
                if isinstance(event, dict) and event.get("type") == "error":
                    success = False
                    result.error = event.get("message", "Unknown error")
        except Exception as e:
            success = False
            result.error = str(e)
            logger.exception("Agentic loop failed with exception")
        
        # Reload workflow to get updated task states
        workflow = self.store.get_workflow(workflow.id, workflow.owner_id)
        
        now = datetime.now()
        elapsed = (now - result.started_at).total_seconds() if result.started_at else 0.0

        if success and workflow.status != WorkflowStatus.FAILED:
            workflow.status = WorkflowStatus.ACTIVE  # Ready to run again
            self.store.save_workflow(workflow)

            result.status = WorkflowStatus.COMPLETED
            result.completed_at = now
            result.execution_time = elapsed
            result.output = {"message": "Workflow completed successfully"}
            self.store.save_execution(result)
            logger.info(f"Completed agentic execution {result.execution_id}")
        else:
            workflow.status = WorkflowStatus.FAILED
            self.store.save_workflow(workflow)

            result.status = WorkflowStatus.FAILED
            if not result.error:
                result.error = "Agentic execution failed. See task errors for details."
            result.completed_at = now
            result.execution_time = elapsed
            self.store.save_execution(result)
            logger.error(f"Failed agentic execution {result.execution_id}")
        
    def _cleanup_stale_executions(self, workflow_id: str, owner_id: str):
        """Mark any old RUNNING executions as FAILED before starting a new one."""
        try:
            conn = self.store._get_conn()
            conn.execute("""
                UPDATE executions
                SET status = 'failed',
                    error = 'Superseded by a newer execution',
                    completed_at = ?
                WHERE workflow_id = ? AND status = 'running'
            """, (datetime.now().isoformat(), workflow_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to cleanup stale executions: {e}")

    async def resume_execution(self, pause_id: str, resume_input: dict, owner_id: str = "") -> ExecutionResult:
        """
        Resume is deprecated in pure agentic mode unless we implement it via a specialized tool.
        """
        raise ValueError("Resume not supported in pure agentic mode yet.")

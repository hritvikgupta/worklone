"""
Workflow Monitoring Tools — tools for employees to monitor, pause, and resume workflows.
"""

from typing import List
from backend.tools.system_tools.base import BaseTool, ToolResult
from backend.store.workflow_store import WorkflowStore
from backend.workflows.utils import generate_id


class GetExecutionStatusTool(BaseTool):
    name = "get_execution_status"
    description = "Check the current status of a workflow execution (running, paused, completed, failed)."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID to check"},
            },
            "required": ["workflow_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        executions = store.get_workflow_executions(parameters["workflow_id"], limit=5)
        if not executions:
            return ToolResult(success=True, output="No executions found.", data={"executions": []})
        output = f"Last {len(executions)} executions:\n\n"
        for ex in executions:
            output += f"• {ex['id']} — Status: **{ex['status']}** | Trigger: {ex.get('trigger_type','?')} | Duration: {ex.get('execution_time',0):.1f}s\n"
            if ex.get("error"):
                output += f"  Error: {ex['error']}\n"
        return ToolResult(success=True, output=output, data={"executions": executions})


class ListPausedWorkflowsTool(BaseTool):
    name = "list_paused_workflows"
    description = "List all workflows currently paused waiting for human approval."
    category = "workflow"

    def get_schema(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        owner_id = (context.get("user_id") if context else "") or ""
        paused = store.list_paused_executions(owner_id)
        if not paused:
            return ToolResult(success=True, output="No paused workflows.", data={"paused": []})
        output = f"Paused workflows ({len(paused)}):\n\n"
        for p in paused:
            points = p.get("pause_points", [])
            prompt = points[0].get("prompt", "No details") if points else "No details"
            output += f"• Pause ID: {p['id']} | Workflow: {p['workflow_id']} | Since: {p['paused_at']}\n"
            output += f"  Reason: {prompt}\n\n"
        return ToolResult(success=True, output=output, data={"paused": paused})


class ResumeWorkflowTool(BaseTool):
    name = "resume_workflow"
    description = "Resume a paused workflow with optional input/approval data."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pause_id": {"type": "string", "description": "Paused execution ID"},
                "input": {"type": "object", "description": "Input data for the paused block (approval, form fields, etc.)"},
            },
            "required": ["pause_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        from backend.workflows.engine.executor import WorkflowExecutor
        store = WorkflowStore()
        owner_id = (context.get("user_id") if context else "") or ""
        executor = WorkflowExecutor(store)
        try:
            result = await executor.resume_execution(
                pause_id=parameters["pause_id"],
                resume_input=parameters.get("input", {}),
                owner_id=owner_id or None,
            )
            status = result.status.value
            return ToolResult(
                success=True,
                output=f"Workflow resumed. New status: **{status}**. Execution: {result.execution_id}",
                data={"execution_id": result.execution_id, "status": status},
            )
        except ValueError as e:
            return ToolResult(success=False, output=str(e))


class PauseWorkflowTool(BaseTool):
    name = "pause_workflow"
    description = "Request to pause a running workflow (sets status to paused)."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID to pause"},
            },
            "required": ["workflow_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        store.update_workflow_status(parameters["workflow_id"], "paused")
        return ToolResult(success=True, output=f"Workflow {parameters['workflow_id']} marked as paused.")


class CancelWorkflowTool(BaseTool):
    name = "cancel_workflow"
    description = "Cancel a running or paused workflow execution."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID to cancel"},
            },
            "required": ["workflow_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        owner_id = (context.get("user_id") if context else "") or ""
        # Cancel any paused executions
        paused = store.list_paused_executions(owner_id, workflow_id=parameters["workflow_id"])
        for p in paused:
            store.update_paused_execution_status(p["id"], "cancelled")
        store.update_workflow_status(parameters["workflow_id"], "cancelled")
        return ToolResult(success=True, output=f"Workflow {parameters['workflow_id']} cancelled.")


def create_monitoring_tools() -> List[BaseTool]:
    return [
        GetExecutionStatusTool(),
        ListPausedWorkflowsTool(),
        ResumeWorkflowTool(),
        PauseWorkflowTool(),
        CancelWorkflowTool(),
    ]

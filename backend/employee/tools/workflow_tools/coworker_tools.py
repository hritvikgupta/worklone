"""
Workflow Creation Tools — tools for Katy to create and manage workflows.
"""

from typing import List
from backend.employee.tools.system_tools.base import BaseTool, ToolResult
from backend.workflows.store import WorkflowStore
from backend.workflows.utils import generate_id


class CreateWorkflowTool(BaseTool):
    """Create a new workflow."""
    name = "create_workflow"
    description = "Create a new automated workflow. Returns workflow ID."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Workflow name (e.g., 'daily-github-summary')"},
                "description": {"type": "string", "description": "What this workflow does"},
                "user_id": {"type": "string", "description": "User who owns this workflow"},
            },
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        user_id = parameters.get("user_id") or (context.get("user_id") if context else "")
        actor_type = parameters.get("created_by_actor_type") or (context.get("actor_type") if context else "") or "employee"
        actor_id = parameters.get("created_by_actor_id") or (context.get("actor_id") if context else "") or (context.get("employee_id") if context else "") or "employee"
        actor_name = parameters.get("created_by_actor_name") or (context.get("actor_name") if context else "") or (context.get("employee_name") if context else "") or "Employee"
        workflow_id = generate_id("wf")
        
        store.create_workflow(
            workflow_id=workflow_id,
            name=parameters.get("name"),
            description=parameters.get("description", ""),
            user_id=user_id,
            created_by_actor_type=actor_type,
            created_by_actor_id=actor_id,
            created_by_actor_name=actor_name,
        )
        return ToolResult(success=True, output=f"✅ Created workflow '{parameters['name']}' (ID: {workflow_id})", data={"workflow_id": workflow_id})


class AddBlockTool(BaseTool):
    """Add a block to a workflow."""
    name = "add_block"
    description = "Add a step (block) to a workflow. Returns block ID."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow to add block to"},
                "block_type": {
                    "type": "string",
                    "enum": ["trigger", "tool", "agent", "function", "http", "condition", "variable", "start", "end"],
                    "description": "Type of block",
                },
                "name": {"type": "string", "description": "Block name"},
                "config": {"type": "object", "description": "Block configuration (tool_name, action, prompt, schedule, etc.)"},
            },
            "required": ["workflow_id", "block_type", "name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        block_id = generate_id("blk")
        
        store.add_block(
            workflow_id=parameters["workflow_id"],
            block_id=block_id,
            block_type=parameters["block_type"],
            name=parameters["name"],
            config=parameters.get("config", {}),
        )
        return ToolResult(success=True, output=f"✅ Added {parameters['block_type']} block '{parameters['name']}' (ID: {block_id})", data={"block_id": block_id})


class ConnectBlocksTool(BaseTool):
    """Connect two blocks in a workflow."""
    name = "connect_blocks"
    description = "Connect two blocks so output from one flows to the next."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
                "from_block_id": {"type": "string", "description": "Source block ID"},
                "to_block_id": {"type": "string", "description": "Destination block ID"},
            },
            "required": ["workflow_id", "from_block_id", "to_block_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        conn_id = generate_id("conn")
        
        store.add_connection(
            workflow_id=parameters["workflow_id"],
            from_block_id=parameters["from_block_id"],
            to_block_id=parameters["to_block_id"],
            connection_id=conn_id,
        )
        return ToolResult(success=True, output=f"✅ Connected {parameters['from_block_id']} → {parameters['to_block_id']}", data={"connection_id": conn_id})


class SetTriggerTool(BaseTool):
    """Set a trigger for a workflow."""
    name = "set_trigger"
    description = "Set when a workflow runs (schedule, webhook, manual, API)."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
                "trigger_type": {
                    "type": "string",
                    "enum": ["schedule", "webhook", "manual", "api"],
                    "description": "How the workflow is triggered",
                },
                "config": {"type": "object", "description": "Trigger config (e.g., {cron: '0 9 * * *'} for schedule)"},
            },
            "required": ["workflow_id", "trigger_type"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        trigger_id = generate_id("trig")
        
        store.add_trigger(
            workflow_id=parameters["workflow_id"],
            trigger_id=trigger_id,
            trigger_type=parameters["trigger_type"],
            config=parameters.get("config", {}),
        )
        return ToolResult(success=True, output=f"✅ Set {parameters['trigger_type']} trigger for workflow", data={"trigger_id": trigger_id})


class ExecuteWorkflowTool(BaseTool):
    """Activate/execute a workflow."""
    name = "execute_workflow"
    description = "Activate and execute a workflow immediately."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID to execute"},
            },
            "required": ["workflow_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        actor_type = parameters.get("handoff_actor_type") or (context.get("actor_type") if context else "") or "employee"
        actor_id = parameters.get("handoff_actor_id") or (context.get("actor_id") if context else "") or (context.get("employee_id") if context else "") or "employee"
        actor_name = parameters.get("handoff_actor_name") or (context.get("actor_name") if context else "") or (context.get("employee_name") if context else "") or "Employee"
        store.update_workflow_status(
            parameters["workflow_id"],
            "active",
            handoff_actor_type=actor_type,
            handoff_actor_id=actor_id,
            handoff_actor_name=actor_name,
        )
        return ToolResult(success=True, output=f"✅ Workflow {parameters['workflow_id']} activated. The Executor Agent will run it.", data={"workflow_id": parameters["workflow_id"]})


class ListWorkflowsTool(BaseTool):
    """List all workflows for a user."""
    name = "list_workflows"
    description = "List all workflows created by the user."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "User ID to list workflows for"},
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        user_id = parameters.get("user_id") or (context.get("user_id") if context else "")
        workflows = store.list_workflows_for_user(user_id)
        
        if not workflows:
            return ToolResult(success=True, output="No workflows found.", data={"workflows": []})
        
        output = f"Your workflows ({len(workflows)}):\n\n"
        for wf in workflows:
            output += f"• **{wf['name']}** (ID: {wf['id']})\n"
            output += f"  Status: {wf.get('status', 'unknown')} | Created: {wf.get('created_at', 'unknown')}\n\n"
        return ToolResult(success=True, output=output, data={"workflows": workflows})


class MonitorWorkflowTool(BaseTool):
    """Monitor workflow execution status."""
    name = "monitor_workflow"
    description = "Check the execution history and status of a workflow."
    category = "workflow"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID to monitor"},
            },
            "required": ["workflow_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        store = WorkflowStore()
        executions = store.get_workflow_executions(parameters["workflow_id"])
        
        if not executions:
            return ToolResult(success=True, output="No executions found for this workflow.", data={"executions": []})
        
        output = f"Execution history ({len(executions)}):\n\n"
        for ex in executions[-5:]:  # Last 5 executions
            output += f"• Run at {ex.get('started_at', 'unknown')} — Status: {ex.get('status', 'unknown')}\n"
            if ex.get("error"):
                output += f"  Error: {ex['error']}\n"
        return ToolResult(success=True, output=output, data={"executions": executions})


def create_workflow_tools() -> List[BaseTool]:
    """Create and return all workflow creation tools."""
    return [
        CreateWorkflowTool(),
        AddBlockTool(),
        ConnectBlocksTool(),
        SetTriggerTool(),
        ExecuteWorkflowTool(),
        ListWorkflowsTool(),
        MonitorWorkflowTool(),
    ]

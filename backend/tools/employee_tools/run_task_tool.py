"""
RunTaskTool — executes a task asynchronously in the background.

The employee calls this to start working on a task. The task runs in a
background asyncio task so the user can keep chatting. Status updates
are written to the employee's activity log and task status.
"""

from backend.tools.system_tools.base import BaseTool, ToolResult

RUN_TASK_MARKER = "__RUN_TASK_ASYNC__"


class RunTaskTool(BaseTool):
    name = "run_task_async"
    description = (
        "Start executing a task in the background. The task will run asynchronously "
        "while you continue chatting with the user. Use this after the user approves "
        "your plan. Provide the task_id and instructions for what to do."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to execute",
                },
                "instructions": {
                    "type": "string",
                    "description": "Detailed instructions for what to do in this task",
                },
            },
            "required": ["task_id", "instructions"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        task_id = parameters.get("task_id", "")
        instructions = parameters.get("instructions", "")

        if not task_id:
            return ToolResult(False, "", error="task_id is required")
        if not instructions:
            return ToolResult(False, "", error="instructions are required")

        # Return marker — the ReAct loop will detect this and spawn background work
        return ToolResult(
            success=True,
            output=RUN_TASK_MARKER,
            data={
                "marker": RUN_TASK_MARKER,
                "task_id": task_id,
                "instructions": instructions,
            },
        )

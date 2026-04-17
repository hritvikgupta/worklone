"""
AskUserTool — pauses the ReAct loop to ask the user for approval or input.

When the employee calls this tool, the ReAct loop detects the special
_ASK_USER marker in the result, pauses execution, and emits a
'confirmation_required' SSE event to the frontend. The loop resumes
only when the user responds.
"""

from backend.core.tools.system_tools.base import BaseTool, ToolResult

ASK_USER_MARKER = "__ASK_USER__"


class AskUserTool(BaseTool):
    name = "ask_user"
    description = (
        "Pause and ask the user a question, request approval, or get input. "
        "Use this before executing a plan, making irreversible changes, or when "
        "you need clarification. The user will see your message and can approve, "
        "reject, or provide input."
    )
    category = "employee"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The question or approval request to show the user",
                },
                "type": {
                    "type": "string",
                    "enum": ["approval", "input", "choice"],
                    "description": "Type of interaction: approval (yes/no), input (free text), choice (pick from options)",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Options for 'choice' type",
                },
                "default_action": {
                    "type": "string",
                    "enum": ["approve", "reject"],
                    "description": "Default if user doesn't respond (for approval type)",
                },
            },
            "required": ["message"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        message = parameters.get("message", "")
        ask_type = parameters.get("type", "approval")
        options = parameters.get("options", [])

        # Return a special marker that the ReAct loop detects
        return ToolResult(
            success=True,
            output=ASK_USER_MARKER,
            data={
                "marker": ASK_USER_MARKER,
                "message": message,
                "type": ask_type,
                "options": options,
            },
        )

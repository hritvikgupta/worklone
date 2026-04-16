from typing import Any, Dict
import httpx
from urllib.parse import urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class MemoryDeleteTool(BaseTool):
    name = "memory_delete"
    description = "Delete memories by conversationId."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "conversationId": {
                    "type": "string",
                    "description": "Conversation identifier (e.g., user-123, session-abc). Deletes all memories for this conversation."
                },
                "id": {
                    "type": "string",
                    "description": "Legacy parameter for conversation identifier. Use conversationId instead. Provided for backwards compatibility."
                }
            },
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        workspace_id = context.get("workspaceId") if context else None
        if not workspace_id:
            return ToolResult(success=False, output="", error="workspaceId is required in execution context")

        conversation_id = parameters.get("conversationId") or parameters.get("id")
        if not conversation_id:
            return ToolResult(success=False, output="", error="conversationId or id is required")

        query_params = {
            "workspaceId": workspace_id,
            "conversationId": conversation_id
        }
        query_string = urlencode(query_params)
        url = f"/api/memory?{query_string}"

        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
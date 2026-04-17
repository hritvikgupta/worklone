from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class MemoryAddTool(BaseTool):
    name = "memory_add"
    description = "Add a new memory to the database or append to existing memory with the same ID."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "conversationId": {
                    "type": "string",
                    "description": "Conversation identifier (e.g., user-123, session-abc). If a memory with this conversationId already exists, the new message will be appended to it.",
                },
                "id": {
                    "type": "string",
                    "description": "Legacy parameter for conversation identifier. Use conversationId instead. Provided for backwards compatibility.",
                },
                "role": {
                    "type": "string",
                    "description": "Role for agent memory (user, assistant, or system)",
                },
                "content": {
                    "type": "string",
                    "description": "Content for agent memory",
                },
            },
            "required": ["role", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        workspace_id = context.get("workspaceId")
        if not workspace_id:
            return ToolResult(success=False, output="", error="workspaceId is required in execution context")

        conversation_id = parameters.get("conversationId") or parameters.get("id")
        if not conversation_id:
            return ToolResult(success=False, output="", error="conversationId or id is required")

        body = {
            "key": conversation_id,
            "workspaceId": workspace_id,
            "data": {
                "role": parameters["role"],
                "content": parameters["content"],
            },
        }

        headers = {
            "Content-Type": "application/json",
        }

        url = "/api/memory"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    result = response.json()
                    data = result.get("data") or result
                    memories_data = data.get("data")
                    if memories_data is None:
                        memories = []
                    elif isinstance(memories_data, list):
                        memories = memories_data
                    else:
                        memories = [memories_data]
                    processed_data = {"memories": memories}
                    return ToolResult(
                        success=True, output=json.dumps(processed_data), data=processed_data
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
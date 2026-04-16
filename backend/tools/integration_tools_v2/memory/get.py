from typing import Any, Dict
import httpx
import os
from urllib.parse import urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class MemoryGetTool(BaseTool):
    name = "Get Memory"
    description = "Retrieve memory by conversationId. Returns matching memories."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "conversationId": {
                    "type": "string",
                    "description": "Conversation identifier (e.g., user-123, session-abc). Returns memories for this conversation.",
                },
                "id": {
                    "type": "string",
                    "description": "Legacy parameter for conversation identifier. Use conversationId instead. Provided for backwards compatibility.",
                },
            },
            "required": [],
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
            "query": conversation_id,
            "limit": "1000",
        }
        query_string = urlencode(query_params)
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        url = f"{api_base_url.rstrip('/')}/api/memory?{query_string}"

        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    result = response.json()
                    memories = result.get("data", {}).get("memories", [])
                    if not isinstance(memories, list) or len(memories) == 0:
                        data = {
                            "memories": [],
                            "message": "No memories found",
                        }
                    else:
                        data = {
                            "memories": memories,
                            "message": f"Found {len(memories)} memories",
                        }
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
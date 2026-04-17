from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class MemoryGetAllTool(BaseTool):
    name = "memory_get_all"
    description = "Retrieve all memories from the database"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if context is None:
            context = {}
        workspace_id = context.get("workspaceId")
        if not workspace_id:
            return ToolResult(success=False, output="", error="workspaceId is required in execution context")
        url = f"/api/memory?workspaceId={quote(str(workspace_id))}"
        headers = {
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code in [200, 201, 204]:
                    result = response.json()
                    data = result.get("data") or result
                    memories = data.get("memories") or data or []
                    if not isinstance(memories, list) or len(memories) == 0:
                        output_data = {
                            "memories": [],
                            "message": "No memories found",
                        }
                    else:
                        output_data = {
                            "memories": memories,
                            "message": f"Found {len(memories)} memories",
                        }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
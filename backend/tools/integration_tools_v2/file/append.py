from typing import Any
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class FileAppendTool(BaseTool):
    name = "file_append"
    description = "Append content to an existing workspace file. The file must already exist. Content is added to the end of the file."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fileName": {
                    "type": "string",
                    "description": "Name of an existing workspace file to append to.",
                },
                "content": {
                    "type": "string",
                    "description": "The text content to append to the file.",
                },
            },
            "required": ["fileName", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        headers = {
            "Content-Type": "application/json",
        }
        body = {
            "operation": "append",
            "fileName": parameters["fileName"],
            "content": parameters["content"],
            "workspaceId": parameters.get("workspaceId") or context.get("workspaceId"),
        }
        url = "/api/tools/file/manage"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                if not (200 <= response.status_code < 300) or not data.get("success"):
                    return ToolResult(
                        success=False,
                        output={},
                        error=data.get("error") or "Failed to append to file",
                    )
                return ToolResult(
                    success=True,
                    output=data.get("data", {}),
                    data=data,
                )
        except Exception as e:
            return ToolResult(success=False, output={}, error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Create a new workspace file. If a file with the same name already exists, a numeric suffix is added (e.g., \"data (1).csv\")."
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fileName": {
                    "type": "string",
                    "description": "File name (e.g., \"data.csv\"). If a file with this name exists, a numeric suffix is added automatically."
                },
                "content": {
                    "type": "string",
                    "description": "The text content to write to the file."
                },
                "contentType": {
                    "type": "string",
                    "description": "MIME type for new files (e.g., \"text/plain\"). Auto-detected from file extension if omitted."
                }
            },
            "required": ["fileName", "content"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        headers = {
            "Content-Type": "application/json",
        }
        
        workspace_id = context.get("workspaceId") if context else None
        body = {
            "operation": "write",
            "fileName": parameters["fileName"],
            "content": parameters["content"],
            "contentType": parameters.get("contentType"),
            "workspaceId": workspace_id,
        }
        
        url = "/api/tools/file/manage"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                try:
                    data = response.json()
                except Exception:
                    data = {}
                
                if response.status_code in [200, 201, 204] and data.get("success"):
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_msg = data.get("error", "Failed to write file") if isinstance(data, dict) else response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
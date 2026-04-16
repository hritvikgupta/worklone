from typing import Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HexUpdateProjectTool(BaseTool):
    name = "hex_update_project"
    description = "Update a Hex project status label (e.g., endorsement or custom workspace statuses)."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HEX_API_KEY",
                description="Hex API token (Personal or Workspace)",
                env_var="HEX_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "The UUID of the Hex project to update",
                },
                "status": {
                    "type": "string",
                    "description": "New project status name (custom workspace status label)",
                },
            },
            "required": ["projectId", "status"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        token = context.get("HEX_API_KEY") if context else None
        
        if self._is_placeholder_token(token or ""):
            return ToolResult(success=False, output="", error="Hex API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        project_id = parameters["projectId"]
        status = parameters["status"]
        url = f"https://app.hex.tech/api/v1/projects/{project_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json={"status": status})
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
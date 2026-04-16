from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CursorGetConversationTool(BaseTool):
    name = "cursor_get_conversation"
    description = "Retrieve the conversation history of a cloud agent, including all user prompts and assistant responses. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="cursor_api_key",
                description="Cursor API key",
                env_var="CURSOR_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agentId": {
                    "type": "string",
                    "description": "Unique identifier for the cloud agent (e.g., bc_abc123)",
                },
            },
            "required": ["agentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("cursor_api_key") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Cursor API key not configured.")
        
        agent_id = parameters.get("agentId", "").strip()
        if not agent_id:
            return ToolResult(success=False, output="", error="agentId is required.")
        
        url = f"https://api.cursor.com/v0/agents/{agent_id}/conversation"
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailDeleteInboxTool(BaseTool):
    name = "agentmail_delete_inbox"
    description = "Delete an email inbox in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AGENTMAIL_API_KEY",
                description="AgentMail API key",
                env_var="AGENTMAIL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to delete",
                },
            },
            "required": ["inboxId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        token = context.get("AGENTMAIL_API_KEY") if context else None
        
        if self._is_placeholder_token(token or ""):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {token}",
        }
        
        inbox_id = parameters.get("inboxId", "").strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output='{"deleted": true}')
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", "Failed to delete inbox")
                    except Exception:
                        error_msg = response.text
                    return ToolResult(
                        success=False,
                        output='{"deleted": false}',
                        error=error_msg,
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
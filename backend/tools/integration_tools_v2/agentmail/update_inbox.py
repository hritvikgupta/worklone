from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailUpdateInboxTool(BaseTool):
    name = "Update Inbox"
    description = "Update the display name of an email inbox in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="api_key",
                description="AgentMail API key",
                env_var="AGENTMAIL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        if context is None:
            return ""
        api_key = context.get("api_key")
        if self._is_placeholder_token(api_key or ""):
            return ""
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to update",
                },
                "displayName": {
                    "type": "string",
                    "description": "New display name for the inbox",
                },
            },
            "required": ["inboxId", "displayName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        inbox_id = parameters["inboxId"].strip()
        display_name = parameters["displayName"]
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}"
        body = {
            "display_name": display_name,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
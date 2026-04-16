from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailSendDraftTool(BaseTool):
    name = "agentmail_send_draft"
    description = "Send an existing email draft in AgentMail"
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

    def _resolve_access_token(self, context: dict | None) -> str:
        if context:
            token = context.get("AGENTMAIL_API_KEY")
            if token and not self._is_placeholder_token(token):
                return token
        token = os.getenv("AGENTMAIL_API_KEY")
        if token and not self._is_placeholder_token(token):
            return token
        return ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox containing the draft",
                },
                "draftId": {
                    "type": "string",
                    "description": "ID of the draft to send",
                },
            },
            "required": ["inboxId", "draftId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        inbox_id = str(parameters["inboxId"]).strip()
        draft_id = str(parameters["draftId"]).strip()
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/drafts/{draft_id}/send"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={})
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", "Failed to send draft")
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailDeleteThreadTool(BaseTool):
    name = "agentmail_delete_thread"
    description = "Delete an email thread in AgentMail (moves to trash, or permanently deletes if already in trash)"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = context.get("AGENTMAIL_API_KEY") if context else None
        if self._is_placeholder_token(token or ""):
            token = os.getenv("AGENTMAIL_API_KEY")
        if self._is_placeholder_token(token or ""):
            raise ValueError("AgentMail API key not configured.")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox containing the thread",
                },
                "threadId": {
                    "type": "string",
                    "description": "ID of the thread to delete",
                },
                "permanent": {
                    "type": "boolean",
                    "description": "Force permanent deletion instead of moving to trash",
                },
            },
            "required": ["inboxId", "threadId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        inbox_id = parameters["inboxId"].strip()
        thread_id = parameters["threadId"].strip()
        permanent = parameters.get("permanent", False)
        
        query_string = "?permanent=true" if permanent else ""
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/threads/{thread_id}{query_string}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output='{"deleted": true}',
                        data={"deleted": True},
                    )
                else:
                    error_msg = response.text
                    try:
                        data = response.json()
                        error_msg = data.get("message", "Failed to delete thread")
                    except Exception:
                        pass
                    return ToolResult(
                        success=False,
                        output='{"deleted": false}',
                        error=error_msg,
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class OutlookDeleteTool(BaseTool):
    name = "outlook_delete"
    description = "Delete an Outlook message (move to Deleted Items)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="OUTLOOK_ACCESS_TOKEN",
                description="Access token for Outlook API",
                env_var="OUTLOOK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "outlook",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("OUTLOOK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "messageId": {
                    "type": "string",
                    "description": "ID of the message to delete",
                },
            },
            "required": ["messageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        message_id = parameters["messageId"]
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 204]:
                    data = {
                        "message": "Email moved to Deleted Items successfully",
                        "messageId": message_id,
                        "status": "deleted",
                    }
                    return ToolResult(success=True, output=str(data), data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text or "Failed to delete email")
                    except Exception:
                        error_msg = response.text or "Failed to delete email"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
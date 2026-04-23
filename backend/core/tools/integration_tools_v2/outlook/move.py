from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class OutlookMoveTool(BaseTool):
    name = "outlook_move"
    description = "Move emails between Outlook folders"
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
                    "description": "ID of the message to move",
                },
                "destinationId": {
                    "type": "string",
                    "description": "ID of the destination folder",
                },
            },
            "required": ["messageId", "destinationId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        message_id = parameters["messageId"]
        destination_id = parameters["destinationId"]
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/move"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, headers=headers, json={"destinationId": destination_id}
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except Exception:
                        pass
                    error_msg = (
                        error_data.get("error", {}).get("message", response.text)
                        if error_data
                        else response.text
                    )
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
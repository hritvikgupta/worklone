from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsDeleteChatMessageTool(BaseTool):
    name = "microsoft_teams_delete_chat_message"
    description = "Soft delete a message in a Microsoft Teams chat"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_TEAMS_ACCESS_TOKEN",
                description="Access token for Microsoft Teams",
                env_var="MICROSOFT_TEAMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-teams",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_TEAMS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "chatId": {
                    "type": "string",
                    "description": 'The ID of the chat containing the message (e.g., "19:abc123def456@thread.v2" - from chat listings)',
                },
                "messageId": {
                    "type": "string",
                    "description": 'The ID of the message to delete (e.g., "1234567890123" - a numeric string from message responses)',
                },
            },
            "required": ["chatId", "messageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        chat_id = parameters["chatId"]
        message_id = parameters["messageId"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch user ID
                me_url = "https://graph.microsoft.com/v1.0/me"
                me_response = await client.get(me_url, headers=headers)
                
                if me_response.status_code != 200:
                    try:
                        error_data = me_response.json()
                        error_msg = error_data.get("error", {}).get("message", str(me_response.text))
                    except:
                        error_msg = me_response.text
                    return ToolResult(success=False, output="", error=error_msg)
                
                user_data = me_response.json()
                user_id = user_data["id"]
                
                # Soft delete the message
                delete_url = f"https://graph.microsoft.com/v1.0/users/{quote(user_id)}/chats/{quote(chat_id)}/messages/{quote(message_id)}/softDelete"
                
                del_headers = headers.copy()
                del_headers["Content-Type"] = "application/json"
                
                delete_response = await client.post(delete_url, headers=del_headers, json={})
                
                if delete_response.status_code in [200, 201, 204]:
                    output_data = {
                        "deleted": True,
                        "messageId": message_id,
                        "metadata": {
                            "messageId": message_id,
                            "chatId": chat_id,
                        },
                    }
                    return ToolResult(success=True, output="", data=output_data)
                else:
                    try:
                        error_data = delete_response.json()
                        error_msg = error_data.get("error", {}).get("message", str(delete_response.text))
                    except:
                        error_msg = delete_response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
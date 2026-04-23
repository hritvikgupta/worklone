from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsGetMessageTool(BaseTool):
    name = "microsoft_teams_get_message"
    description = "Get a specific message from a Microsoft Teams chat or channel"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_TEAMS_ACCESS_TOKEN",
                description="Access token for the Microsoft Teams API",
                env_var="MICROSOFT_TEAMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-teams",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("MICROSOFT_TEAMS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "teamId": {
                    "type": "string",
                    "description": 'The ID of the team for channel messages (e.g., "12345678-abcd-1234-efgh-123456789012" - a GUID)',
                },
                "channelId": {
                    "type": "string",
                    "description": 'The ID of the channel for channel messages (e.g., "19:abc123def456@thread.tacv2")',
                },
                "chatId": {
                    "type": "string",
                    "description": 'The ID of the chat for chat messages (e.g., "19:abc123def456@thread.v2")',
                },
                "messageId": {
                    "type": "string",
                    "description": 'The ID of the message to retrieve (e.g., "1234567890123" - a numeric string from message responses)',
                },
            },
            "required": ["messageId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        team_id = (parameters.get("teamId") or "").strip()
        channel_id = (parameters.get("channelId") or "").strip()
        chat_id = (parameters.get("chatId") or "").strip()
        message_id = (parameters.get("messageId") or "").strip()
        
        if not message_id:
            return ToolResult(success=False, output="", error="Message ID is required")
        
        if team_id and channel_id:
            url = f"https://graph.microsoft.com/v1.0/teams/{urllib.parse.quote(team_id)}/channels/{urllib.parse.quote(channel_id)}/messages/{urllib.parse.quote(message_id)}"
        elif chat_id:
            url = f"https://graph.microsoft.com/v1.0/chats/{urllib.parse.quote(chat_id)}/messages/{urllib.parse.quote(message_id)}"
        else:
            return ToolResult(success=False, output="", error="Either (teamId and channelId) or chatId is required")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
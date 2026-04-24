from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsReplyToMessageTool(BaseTool):
    name = "microsoft_teams_reply_to_message"
    description = "Reply to an existing message in a Microsoft Teams channel"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_TEAMS_ACCESS_TOKEN",
                description="Access token",
                env_var="MICROSOFT_TEAMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-teams",
            context=context,
            context_token_keys=("provider_token",),
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
                    "description": 'The ID of the team (e.g., "12345678-abcd-1234-efgh-123456789012" - a GUID from team listings or channel info)',
                },
                "channelId": {
                    "type": "string",
                    "description": 'The ID of the channel (e.g., "19:abc123def456@thread.tacv2" - from channel listings)',
                },
                "messageId": {
                    "type": "string",
                    "description": 'The ID of the message to reply to (e.g., "1234567890123" - a numeric string from message responses)',
                },
                "content": {
                    "type": "string",
                    "description": "The reply content (plain text or HTML formatted message)",
                },
            },
            "required": ["teamId", "channelId", "messageId", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        team_id = parameters["teamId"].strip()
        channel_id = parameters["channelId"].strip()
        message_id = parameters["messageId"].strip()
        content = parameters["content"]
        
        url = f"https://graph.microsoft.com/v1.0/teams/{quote(team_id)}/channels/{quote(channel_id)}/messages/{quote(message_id)}/replies"
        
        json_body = {
            "body": {
                "contentType": "text",
                "content": content,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
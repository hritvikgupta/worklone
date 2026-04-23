from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token
from urllib.parse import quote

class MicrosoftTeamsSetReactionTool(BaseTool):
    name = "microsoft_teams_set_reaction"
    description = "Add an emoji reaction to a message in Microsoft Teams"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_TEAMS_ACCESS_TOKEN",
                description="The access token for the Microsoft Teams API",
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
                "teamId": {
                    "type": "string",
                    "description": "The ID of the team for channel messages (e.g., \"12345678-abcd-1234-efgh-123456789012\" - a GUID)",
                },
                "channelId": {
                    "type": "string",
                    "description": "The ID of the channel for channel messages (e.g., \"19:abc123def456@thread.tacv2\")",
                },
                "chatId": {
                    "type": "string",
                    "description": "The ID of the chat for chat messages (e.g., \"19:abc123def456@thread.v2\")",
                },
                "messageId": {
                    "type": "string",
                    "description": "The ID of the message to react to (e.g., \"1234567890123\" - a numeric string from message responses)",
                },
                "reactionType": {
                    "type": "string",
                    "description": "The emoji reaction (e.g., ❤️, 👍, 😊)",
                },
            },
            "required": ["messageId", "reactionType"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        team_id = (parameters.get("teamId") or "").strip()
        channel_id = (parameters.get("channelId") or "").strip()
        chat_id = (parameters.get("chatId") or "").strip()
        message_id = (parameters.get("messageId") or "").strip()
        reaction_type = (parameters.get("reactionType") or "").strip()
        
        if not message_id:
            return ToolResult(success=False, output="", error="Message ID is required")
        
        if not reaction_type:
            return ToolResult(success=False, output="", error="Reaction type is required")
        
        if team_id and channel_id:
            url = f"https://graph.microsoft.com/v1.0/teams/{quote(team_id)}/channels/{quote(channel_id)}/messages/{quote(message_id)}/setReaction"
        elif chat_id:
            url = f"https://graph.microsoft.com/v1.0/chats/{quote(chat_id)}/messages/{quote(message_id)}/setReaction"
        else:
            return ToolResult(success=False, output="", error="Either (teamId and channelId) or chatId is required")
        
        body = {
            "reactionType": reaction_type,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    metadata = {
                        "messageId": message_id,
                    }
                    if team_id:
                        metadata["teamId"] = team_id
                    if channel_id:
                        metadata["channelId"] = channel_id
                    if chat_id:
                        metadata["chatId"] = chat_id
                    output_data = {
                        "success": True,
                        "reactionType": reaction_type,
                        "messageId": message_id,
                        "metadata": metadata,
                    }
                    return ToolResult(success=True, output="", data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
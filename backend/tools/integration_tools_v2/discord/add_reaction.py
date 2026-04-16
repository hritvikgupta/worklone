from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DiscordAddReactionTool(BaseTool):
    name = "discord_add_reaction"
    description = "Add a reaction emoji to a Discord message"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="bot_token",
                description="The bot token for authentication",
                env_var="DISCORD_BOT_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "discord",
            context=context,
            context_token_keys=("bot_token",),
            env_token_keys=("DISCORD_BOT_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channelId": {
                    "type": "string",
                    "description": "The Discord channel ID containing the message, e.g., 123456789012345678",
                },
                "messageId": {
                    "type": "string",
                    "description": "The ID of the message to react to, e.g., 123456789012345678",
                },
                "emoji": {
                    "type": "string",
                    "description": "The emoji to react with (unicode emoji or custom emoji in name:id format)",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
            },
            "required": ["channelId", "messageId", "emoji", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bot {access_token}",
        }
        
        channel_id = parameters["channelId"]
        message_id = parameters["messageId"]
        emoji = parameters["emoji"]
        encoded_emoji = quote(emoji)
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = {}
                    if response.content:
                        try:
                            data = response.json()
                        except:
                            pass
                    return ToolResult(success=True, output="Reaction added successfully", data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
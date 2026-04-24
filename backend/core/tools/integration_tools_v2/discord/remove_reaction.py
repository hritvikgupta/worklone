from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordRemoveReactionTool(BaseTool):
    name = "discord_remove_reaction"
    description = "Remove a reaction from a Discord message"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DISCORD_BOT_TOKEN",
                description="The bot token for authentication",
                env_var="DISCORD_BOT_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_bot_token(self, context: dict | None) -> str:
        if not context:
            return ""
        token = context.get("DISCORD_BOT_TOKEN")
        if not token or self._is_placeholder_token(token):
            return ""
        return token

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
                    "description": "The ID of the message with the reaction, e.g., 123456789012345678",
                },
                "emoji": {
                    "type": "string",
                    "description": "The emoji to remove (unicode emoji or custom emoji in name:id format)",
                },
                "userId": {
                    "type": "string",
                    "description": "The user ID whose reaction to remove (omit to remove bot's own reaction), e.g., 123456789012345678",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
            },
            "required": ["channelId", "messageId", "emoji", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        bot_token = self._resolve_bot_token(context)
        if not bot_token:
            return ToolResult(success=False, output="", error="Discord bot token not configured.")

        encoded_emoji = quote(parameters["emoji"])
        user_part = f"/{parameters['userId']}" if parameters.get("userId") else "/@me"
        url = f"https://discord.com/api/v10/channels/{parameters['channelId']}/messages/{parameters['messageId']}/reactions/{encoded_emoji}{user_part}"

        headers = {
            "Authorization": f"Bot {bot_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output="Reaction removed successfully")
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
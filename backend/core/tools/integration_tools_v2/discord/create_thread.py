from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordCreateThreadTool(BaseTool):
    name = "discord_create_thread"
    description = "Create a thread in a Discord channel"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="botToken",
                description="The bot token for authentication",
                env_var="DISCORD_BOT_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channelId": {
                    "type": "string",
                    "description": "The Discord channel ID to create the thread in, e.g., 123456789012345678"
                },
                "name": {
                    "type": "string",
                    "description": "The name of the thread (1-100 characters)"
                },
                "messageId": {
                    "type": "string",
                    "description": "The message ID to create a thread from (if creating from existing message), e.g., 123456789012345678"
                },
                "autoArchiveDuration": {
                    "type": "number",
                    "description": "Duration in minutes to auto-archive the thread (60, 1440, 4320, 10080)"
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678"
                }
            },
            "required": ["channelId", "name", "serverId"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        bot_token = context.get("botToken") if context else None
        if self._is_placeholder_token(bot_token or ""):
            return ToolResult(success=False, output="", error="Bot token not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bot {bot_token}",
        }

        channel_id = parameters["channelId"]
        if parameters.get("messageId"):
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{parameters['messageId']}/threads"
        else:
            url = f"https://discord.com/api/v10/channels/{channel_id}/threads"

        body = {
            "name": parameters["name"],
        }
        if "autoArchiveDuration" in parameters:
            body["auto_archive_duration"] = int(parameters["autoArchiveDuration"])

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordJoinThreadTool(BaseTool):
    name = "discord_join_thread"
    description = "Join a thread in Discord"
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

    def _resolve_bot_token(self, context: dict | None) -> str:
        token = (context or {}).get("botToken")
        if self._is_placeholder_token(token or ""):
            token = os.getenv("DISCORD_BOT_TOKEN")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "threadId": {
                    "type": "string",
                    "description": "The thread ID to join, e.g., 123456789012345678",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
            },
            "required": ["threadId", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        bot_token = self._resolve_bot_token(context)

        if self._is_placeholder_token(bot_token):
            return ToolResult(success=False, output="", error="Discord bot token not configured.")

        headers = {
            "Authorization": f"Bot {bot_token}",
        }

        thread_id = parameters["threadId"]
        url = f"https://discord.com/api/v10/channels/{thread_id}/thread-members/@me"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output='{"message": "Joined thread successfully"}',
                        data={"message": "Joined thread successfully"},
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
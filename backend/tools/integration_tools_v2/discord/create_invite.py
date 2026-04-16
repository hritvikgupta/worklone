from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordCreateInviteTool(BaseTool):
    name = "discord_create_invite"
    description = "Create an invite link for a Discord channel"
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

    async def _resolve_bot_token(self, context: dict | None) -> str:
        token = (context or {}).get("provider_token") or os.getenv("DISCORD_BOT_TOKEN")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channelId": {
                    "type": "string",
                    "description": "The Discord channel ID to create an invite for, e.g., 123456789012345678",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
                "maxAge": {
                    "type": "number",
                    "description": "Duration of invite in seconds (0 = never expires, default 86400)",
                },
                "maxUses": {
                    "type": "number",
                    "description": "Max number of uses (0 = unlimited, default 0)",
                },
                "temporary": {
                    "type": "boolean",
                    "description": "Whether invite grants temporary membership",
                },
            },
            "required": ["channelId", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        bot_token = await self._resolve_bot_token(context)

        if self._is_placeholder_token(bot_token):
            return ToolResult(success=False, output="", error="Bot token not configured.")

        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        }

        channel_id = parameters["channelId"]
        url = f"https://discord.com/api/v10/channels/{channel_id}/invites"

        body: dict = {}
        max_age = parameters.get("maxAge")
        if max_age is not None:
            body["max_age"] = int(max_age)
        max_uses = parameters.get("maxUses")
        if max_uses is not None:
            body["max_uses"] = int(max_uses)
        temporary = parameters.get("temporary")
        if temporary is not None:
            body["temporary"] = temporary

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
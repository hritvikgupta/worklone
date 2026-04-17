from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DiscordUpdateMemberTool(BaseTool):
    name = "discord_update_member"
    description = "Update a member in a Discord server (e.g., change nickname)"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "discord",
            context=context,
            context_token_keys=("botToken",),
            env_token_keys=("DISCORD_BOT_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
                "userId": {
                    "type": "string",
                    "description": "The user ID to update, e.g., 123456789012345678",
                },
                "nick": {
                    "type": "string",
                    "description": "New nickname for the member (null to remove)",
                },
                "mute": {
                    "type": "boolean",
                    "description": "Whether to mute the member in voice channels",
                },
                "deaf": {
                    "type": "boolean",
                    "description": "Whether to deafen the member in voice channels",
                },
            },
            "required": ["serverId", "userId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Discord bot token not configured.")

        headers = {
            "Authorization": f"Bot {access_token}",
            "Content-Type": "application/json",
        }

        server_id = parameters["serverId"]
        user_id = parameters["userId"]
        url = f"https://discord.com/api/v10/guilds/{server_id}/members/{user_id}"

        body = {}
        if "nick" in parameters and parameters["nick"] != "":
            body["nick"] = parameters["nick"]
        if "mute" in parameters and parameters["mute"] is not None:
            body["mute"] = parameters["mute"]
        if "deaf" in parameters and parameters["deaf"] is not None:
            body["deaf"] = parameters["deaf"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
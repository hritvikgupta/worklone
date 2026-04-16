from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DiscordUpdateChannelTool(BaseTool):
    name = "Discord Update Channel"
    description = "Update a Discord channel"
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
                    "description": "The Discord channel ID to update, e.g., 123456789012345678",
                },
                "name": {
                    "type": "string",
                    "description": "The new name for the channel",
                },
                "topic": {
                    "type": "string",
                    "description": "The new topic for the channel",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
            },
            "required": ["channelId", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        bot_token = await self._resolve_bot_token(context)
        
        if self._is_placeholder_token(bot_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://discord.com/api/v10/channels/{parameters['channelId']}"
        
        body: Dict[str, Any] = {}
        name = parameters.get("name")
        if name is not None and name != "":
            body["name"] = name
        topic = parameters.get("topic")
        if topic is not None and topic != "":
            body["topic"] = topic
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
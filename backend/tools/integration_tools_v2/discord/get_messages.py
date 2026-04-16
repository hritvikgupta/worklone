from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DiscordGetMessagesTool(BaseTool):
    name = "discord_get_messages"
    description = "Retrieve messages from a Discord channel"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DISCORD_BOT_TOKEN",
                description="Discord bot token",
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
                "botToken": {
                    "type": "string",
                    "description": "The bot token for authentication",
                },
                "channelId": {
                    "type": "string",
                    "description": "The Discord channel ID to retrieve messages from, e.g., 123456789012345678",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of messages to retrieve (default: 10, max: 100)",
                },
            },
            "required": ["botToken", "channelId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bot {access_token}",
            "Content-Type": "application/json",
        }
        
        channel_id = parameters["channelId"]
        try:
            limit_val = parameters.get("limit")
            if limit_val is None:
                limit = 10
            else:
                limit = int(limit_val)
                limit = min(max(limit, 1), 100)
        except (ValueError, TypeError):
            limit = 10
        
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    messages = response.json()
                    num_messages = len(messages)
                    channel_id_out = messages[0]["channel_id"] if messages else ""
                    output_msg = f"Retrieved {num_messages} messages from Discord channel"
                    data = {
                        "messages": messages,
                        "channel_id": channel_id_out,
                    }
                    return ToolResult(success=True, output=output_msg, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
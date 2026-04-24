from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordCreateChannelTool(BaseTool):
    name = "discord_create_channel"
    description = "Create a new channel in a Discord server"
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
        bot_token = (context or {}).get("botToken")
        if not bot_token:
            bot_token = os.getenv("DISCORD_BOT_TOKEN")
        return bot_token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
                "name": {
                    "type": "string",
                    "description": "The name of the channel (1-100 characters)",
                },
                "type": {
                    "type": "number",
                    "description": "Channel type (0=text, 2=voice, 4=category, 5=announcement, 13=stage)",
                },
                "topic": {
                    "type": "string",
                    "description": "Channel topic (0-1024 characters)",
                },
                "parentId": {
                    "type": "string",
                    "description": "Parent category ID for the channel, e.g., 123456789012345678",
                },
            },
            "required": ["serverId", "name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        bot_token = self._resolve_bot_token(context)
        
        if self._is_placeholder_token(bot_token):
            return ToolResult(success=False, output="", error="Bot token not configured.")
        
        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://discord.com/api/v10/guilds/{parameters['serverId']}/channels"
        
        body = {
            "name": parameters["name"],
        }
        type_val = parameters.get("type")
        if type_val is not None:
            body["type"] = int(type_val)
        topic = parameters.get("topic")
        if topic:
            body["topic"] = topic
        parent_id = parameters.get("parentId")
        if parent_id:
            body["parent_id"] = parent_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
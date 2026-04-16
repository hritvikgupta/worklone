from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordRemoveRoleTool(BaseTool):
    name = "Discord Remove Role"
    description = "Remove a role from a member in a Discord server"
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

    async def _resolve_bot_token(self, context: dict | None) -> str:
        token = context.get("botToken") if context else None
        if self._is_placeholder_token(token or ""):
            token = os.getenv("DISCORD_BOT_TOKEN")
        return token

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
                    "description": "The user ID to remove the role from, e.g., 123456789012345678",
                },
                "roleId": {
                    "type": "string",
                    "description": "The role ID to remove, e.g., 123456789012345678",
                },
            },
            "required": ["serverId", "userId", "roleId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        bot_token = await self._resolve_bot_token(context)
        
        if self._is_placeholder_token(bot_token):
            return ToolResult(success=False, output="", error="Bot token not configured.")
        
        headers = {
            "Authorization": f"Bot {bot_token}",
        }
        
        server_id = parameters["serverId"]
        user_id = parameters["userId"]
        role_id = parameters["roleId"]
        url = f"https://discord.com/api/v10/guilds/{server_id}/members/{user_id}/roles/{role_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = None
                    if response.content:
                        try:
                            data = response.json()
                        except Exception:
                            pass
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
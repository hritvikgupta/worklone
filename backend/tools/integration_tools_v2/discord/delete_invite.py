from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordDeleteInviteTool(BaseTool):
    name = "Discord Delete Invite"
    description = "Delete a Discord invite"
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
        bot_token = context.get("botToken") if context else None
        if not bot_token:
            bot_token = os.environ.get("DISCORD_BOT_TOKEN")
        return bot_token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inviteCode": {
                    "type": "string",
                    "description": "The invite code to delete",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
            },
            "required": ["inviteCode", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        bot_token = await self._resolve_bot_token(context)
        
        if self._is_placeholder_token(bot_token):
            return ToolResult(success=False, output="", error="Bot token not configured.")
        
        headers = {
            "Authorization": f"Bot {bot_token}",
        }
        
        url = f"https://discord.com/api/v10/invites/{parameters['inviteCode']}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = {}
                    try:
                        data = response.json()
                    except:
                        pass
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
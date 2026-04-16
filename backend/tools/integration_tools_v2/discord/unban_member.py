from typing import Any, Dict
import httpx
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DiscordUnbanMemberTool(BaseTool):
    name = "Discord Unban Member"
    description = "Unban a member from a Discord server"
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
                    "description": "The user ID to unban, e.g., 123456789012345678",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for unbanning the member",
                },
            },
            "required": ["serverId", "userId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bot {access_token}",
        }
        reason = parameters.get("reason")
        if reason:
            headers["X-Audit-Log-Reason"] = urllib.parse.quote(reason)
        
        url = f"https://discord.com/api/v10/guilds/{parameters['serverId']}/bans/{parameters['userId']}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code == 204:
                    return ToolResult(
                        success=True,
                        output='{"message": "Member unbanned successfully"}',
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP {response.status_code}: {response.text}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
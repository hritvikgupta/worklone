from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DiscordCreateRoleTool(BaseTool):
    name = "discord_create_role"
    description = "Create a new role in a Discord server"
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
                "name": {
                    "type": "string",
                    "description": "The name of the role",
                },
                "color": {
                    "type": "number",
                    "description": "RGB color value as integer (e.g., 0xFF0000 for red)",
                },
                "hoist": {
                    "type": "boolean",
                    "description": "Whether to display role members separately from online members",
                },
                "mentionable": {
                    "type": "boolean",
                    "description": "Whether the role can be mentioned",
                },
            },
            "required": ["serverId", "name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bot {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://discord.com/api/v10/guilds/{parameters['serverId']}/roles"
        
        body = {
            "name": parameters["name"],
        }
        if "color" in parameters:
            body["color"] = int(parameters["color"])
        if "hoist" in parameters:
            body["hoist"] = parameters["hoist"]
        if "mentionable" in parameters:
            body["mentionable"] = parameters["mentionable"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
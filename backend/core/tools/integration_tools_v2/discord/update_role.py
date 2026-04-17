from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordUpdateRoleTool(BaseTool):
    name = "discord_update_role"
    description = "Update a role in a Discord server"
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
        if context is None:
            return ""
        token = context.get("botToken")
        if self._is_placeholder_token(token or ""):
            return ""
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "botToken": {
                    "type": "string",
                    "description": "The bot token for authentication",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
                "roleId": {
                    "type": "string",
                    "description": "The role ID to update, e.g., 123456789012345678",
                },
                "name": {
                    "type": "string",
                    "description": "The new name for the role",
                },
                "color": {
                    "type": "number",
                    "description": "RGB color value as integer",
                },
                "hoist": {
                    "type": "boolean",
                    "description": "Whether to display role members separately",
                },
                "mentionable": {
                    "type": "boolean",
                    "description": "Whether the role can be mentioned",
                },
            },
            "required": ["botToken", "serverId", "roleId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Bot token not configured.")

        headers = {
            "Authorization": f"Bot {access_token}",
            "Content-Type": "application/json",
        }

        server_id = parameters["serverId"]
        role_id = parameters["roleId"]
        url = f"https://discord.com/api/v10/guilds/{server_id}/roles/{role_id}"

        body = {}
        name_val = parameters.get("name")
        if name_val:
            body["name"] = name_val
        if "color" in parameters:
            body["color"] = int(parameters["color"])
        if "hoist" in parameters:
            body["hoist"] = parameters["hoist"]
        if "mentionable" in parameters:
            body["mentionable"] = parameters["mentionable"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
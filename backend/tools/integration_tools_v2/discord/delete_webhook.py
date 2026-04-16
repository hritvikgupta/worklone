import os
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordDeleteWebhookTool(BaseTool):
    name = "discord_delete_webhook"
    description = "Delete a Discord webhook"
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
        token = context.get("botToken") if context else None
        if not token:
            token = os.environ.get("DISCORD_BOT_TOKEN")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "webhookId": {
                    "type": "string",
                    "description": "The webhook ID to delete, e.g., 123456789012345678",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
            },
            "required": ["webhookId", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bot {access_token}",
        }
        
        webhook_id = parameters["webhookId"]
        url = f"https://discord.com/api/v10/webhooks/{webhook_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output="Webhook deleted successfully",
                        data={"message": "Webhook deleted successfully"},
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
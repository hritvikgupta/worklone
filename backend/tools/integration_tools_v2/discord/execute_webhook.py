from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DiscordExecuteWebhookTool(BaseTool):
    name = "Discord Execute Webhook"
    description = "Execute a Discord webhook to send a message"
    category = "integration"

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "webhookId": {
                    "type": "string",
                    "description": "The webhook ID, e.g., 123456789012345678",
                },
                "content": {
                    "type": "string",
                    "description": "The message content to send",
                },
                "username": {
                    "type": "string",
                    "description": "Override the default username of the webhook",
                },
                "serverId": {
                    "type": "string",
                    "description": "The Discord server ID (guild ID), e.g., 123456789012345678",
                },
            },
            "required": ["webhookId", "content", "serverId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        webhook_id = parameters.get("webhookId")
        webhook_token = parameters.get("webhookToken")
        content = parameters.get("content")
        username = parameters.get("username")

        if not all([webhook_id, webhook_token, content]):
            return ToolResult(success=False, output="", error="Missing required parameters: webhookId, webhookToken, or content.")

        headers = {
            "Content-Type": "application/json",
        }

        url = f"https://discord.com/api/v10/webhooks/{webhook_id}/{webhook_token}?wait=true"

        body: Dict[str, Any] = {
            "content": content,
        }
        if username:
            body["username"] = username

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    return ToolResult(success=True, output="Webhook executed successfully", data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
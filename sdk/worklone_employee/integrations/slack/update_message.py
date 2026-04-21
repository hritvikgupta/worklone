from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackUpdateMessageTool(BaseTool):
    name = "slack_update_message"
    description = "Update a message previously sent by the bot in Slack"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="OAuth access token or bot token for Slack API",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID where the message was posted (e.g., C1234567890)",
                },
                "timestamp": {
                    "type": "string",
                    "description": "Timestamp of the message to update (e.g., 1405894322.002768)",
                },
                "text": {
                    "type": "string",
                    "description": "New message text (supports Slack mrkdwn formatting)",
                },
                "blocks": {
                    "type": "string",
                    "description": "Block Kit layout blocks as a JSON array. When provided, text becomes the fallback notification text.",
                },
            },
            "required": ["channel", "timestamp", "text"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        body = {
            "channel": parameters["channel"],
            "ts": parameters["timestamp"],
            "text": parameters["text"],
        }
        
        blocks_param = parameters.get("blocks")
        if blocks_param:
            try:
                blocks = json.loads(blocks_param) if isinstance(blocks_param, str) else blocks_param
                if isinstance(blocks, list) and len(blocks) > 0:
                    body["blocks"] = blocks
            except json.JSONDecodeError:
                return ToolResult(
                    success=False, output="", error="Invalid JSON in blocks parameter"
                )
        
        url = "https://slack.com/api/chat.update"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                data = response.json()
                
                if response.status_code == 200 and data.get("ok"):
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_msg = data.get("error", "Failed to update message")
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
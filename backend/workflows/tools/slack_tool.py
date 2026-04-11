"""
Slack Tool — Send messages to Slack channels.
"""

from typing import Any
import httpx
import os
from backend.workflows.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackTool(BaseTool):
    """Send messages to Slack channels or users."""
    
    name = "slack_send"
    description = "Send a message to a Slack channel or user. Use for notifications, alerts, or summaries."
    category = "communication"
    
    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_BOT_TOKEN",
                description="Slack Bot OAuth token for sending messages to channels",
                env_var="SLACK_BOT_TOKEN",
                required=True,
                example="xoxb-1234567890-1234567890123-abcdefghijklmnopqrstuv",
                auth_type="oauth",
                auth_url="https://slack.com/oauth/v2/authorize",
                auth_provider="slack",
                auth_scopes="chat:write,channels:read,users:read",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Slack channel (e.g., #general) or user ID",
                },
                "message": {
                    "type": "string",
                    "description": "Message text to send",
                },
                "blocks": {
                    "type": "array",
                    "description": "Slack block kit blocks (optional, for rich messages)",
                },
            },
            "required": ["channel", "message"],
        }
    
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        channel = parameters.get("channel")
        message = parameters.get("message")
        blocks = parameters.get("blocks")
        
        if not channel or not message:
            return ToolResult(
                success=False,
                output="",
                error="Channel and message are required",
            )
        
        # Get token from env or context
        token = os.getenv("SLACK_BOT_TOKEN", "")
        if context and "slack_token" in context:
            token = context["slack_token"]
        
        if not token:
            return ToolResult(
                success=False,
                output="",
                error="SLACK_BOT_TOKEN environment variable not set",
            )
        
        payload = {
            "channel": channel,
            "text": message,
        }
        if blocks:
            payload["blocks"] = blocks
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                
                data = response.json()
                
                if data.get("ok"):
                    return ToolResult(
                        success=True,
                        output=f"Message sent to {channel}: {data.get('ts')}",
                        data=data,
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Slack API error: {data.get('error', 'Unknown error')}",
                    )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to send Slack message: {str(e)}",
            )

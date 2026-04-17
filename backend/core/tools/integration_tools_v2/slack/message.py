from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackMessageTool(BaseTool):
    name = "slack_message"
    description = "Send messages to Slack channels or direct messages. Supports Slack mrkdwn formatting."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="Access token or bot token for Slack API",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "authMethod": {
                    "type": "string",
                    "description": "Authentication method: oauth or bot_token",
                },
                "destinationType": {
                    "type": "string",
                    "description": "Destination type: channel or dm",
                },
                "botToken": {
                    "type": "string",
                    "description": "Bot token for Custom Bot",
                },
                "accessToken": {
                    "type": "string",
                    "description": "OAuth access token or bot token for Slack API",
                },
                "channel": {
                    "type": "string",
                    "description": "Slack channel ID (e.g., C1234567890)",
                },
                "dmUserId": {
                    "type": "string",
                    "description": "Slack user ID for direct messages (e.g., U1234567890)",
                },
                "text": {
                    "type": "string",
                    "description": "Message text to send (supports Slack mrkdwn formatting)",
                },
                "threadTs": {
                    "type": "string",
                    "description": "Thread timestamp to reply to (creates thread reply)",
                },
                "blocks": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    },
                    "description": "Block Kit layout blocks as a JSON array. When provided, text becomes the fallback notification text.",
                },
                "files": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "Files to attach to the message",
                },
            },
            "required": ["text"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        token = parameters.get("accessToken") or parameters.get("botToken") or await self._resolve_access_token(context)
        
        if self._is_placeholder_token(token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                destination_type = parameters.get("destinationType", "channel")
                channel_id = None
                if destination_type == "dm":
                    dm_user_id = parameters.get("dmUserId")
                    if not dm_user_id:
                        return ToolResult(success=False, output="", error="dmUserId is required for destinationType='dm'")
                    conv_resp = await client.post(
                        "https://slack.com/api/conversations.open",
                        params={"token": token, "users": dm_user_id}
                    )
                    conv_data = conv_resp.json()
                    if not conv_data.get("ok"):
                        return ToolResult(
                            success=False,
                            output="",
                            error=conv_data.get("error", "Failed to open conversation")
                        )
                    channel_id = conv_data["channel"]["id"]
                else:
                    channel = parameters.get("channel")
                    if not channel:
                        return ToolResult(success=False, output="", error="channel is required for destinationType='channel'")
                    channel_id = channel

                post_data: Dict[str, Any] = {
                    "channel": channel_id,
                    "text": parameters["text"],
                }
                thread_ts = parameters.get("threadTs")
                if thread_ts:
                    post_data["thread_ts"] = thread_ts

                blocks = parameters.get("blocks")
                if blocks:
                    if isinstance(blocks, str):
                        try:
                            blocks = json.loads(blocks)
                        except json.JSONDecodeError:
                            return ToolResult(success=False, output="", error="Invalid JSON in blocks parameter")
                    if isinstance(blocks, list):
                        post_data["blocks"] = blocks

                # Files support omitted (requires multipart/form-data handling beyond JSON parameters)

                resp = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    params={"token": token},
                    headers=headers,
                    json=post_data
                )
                
                data = resp.json()
                if data.get("ok"):
                    ts = data.get("message", {}).get("ts", "")
                    return ToolResult(success=True, output=ts, data=data)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=data.get("error", resp.text)
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
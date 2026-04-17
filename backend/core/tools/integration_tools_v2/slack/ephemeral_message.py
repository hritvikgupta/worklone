from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackEphemeralMessageTool(BaseTool):
    name = "slack_ephemeral_message"
    description = "Send an ephemeral message visible only to a specific user in a channel. Optionally reply in a thread. The message does not persist across sessions."
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
            context_token_keys=("accessToken", "botToken"),
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
                    "description": "Slack channel ID (e.g., C1234567890)",
                },
                "user": {
                    "type": "string",
                    "description": "User ID who will see the ephemeral message (e.g., U1234567890). Must be a member of the channel.",
                },
                "text": {
                    "type": "string",
                    "description": "Message text to send (supports Slack mrkdwn formatting)",
                },
                "threadTs": {
                    "type": "string",
                    "description": "Thread timestamp to reply in. When provided, the ephemeral message appears as a thread reply.",
                },
                "blocks": {
                    "type": "string",
                    "description": "Block Kit layout blocks as a JSON array. When provided, text becomes the fallback notification text.",
                },
            },
            "required": ["channel", "user", "text"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/chat.postEphemeral"
        
        body: Dict[str, Any] = {
            "channel": parameters["channel"],
            "user": parameters["user"].strip(),
            "text": parameters["text"],
        }
        if parameters.get("threadTs"):
            body["thread_ts"] = parameters["threadTs"]
        
        blocks_str = parameters.get("blocks")
        if blocks_str:
            try:
                body["blocks"] = json.loads(blocks_str)
            except json.JSONDecodeError as e:
                return ToolResult(success=False, output="", error=f"Invalid blocks JSON: {str(e)}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if data.get("ok"):
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_msg = data.get("error", {}).get("message", str(data.get("error", "Unknown error")))
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackCreateChannelCanvasTool(BaseTool):
    name = "Slack Create Channel Canvas"
    description = "Create a canvas pinned to a Slack channel as its resource hub"
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
            context_token_keys=("access_token", "bot_token"),
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
                    "description": "Channel ID to create the canvas in (e.g., C1234567890)",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the channel canvas",
                },
                "content": {
                    "type": "string",
                    "description": "Canvas content in markdown format",
                },
            },
            "required": ["channel"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/conversations.canvases.create"
        
        body: dict = {
            "channel_id": parameters["channel"].strip(),
        }
        title = parameters.get("title")
        if title:
            body["title"] = title
        content = parameters.get("content")
        if content:
            body["document_content"] = {
                "type": "markdown",
                "markdown": content,
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if data.get("ok"):
                    canvas_id = data.get("canvas_id", "")
                    return ToolResult(
                        success=True,
                        output=f"Canvas created successfully with ID: {canvas_id}",
                        data={"canvas_id": canvas_id},
                    )
                else:
                    error_msg = data.get("error")
                    if error_msg == "channel_canvas_already_exists":
                        error_msg = "A canvas already exists for this channel. Use Edit Canvas to modify it."
                    else:
                        error_msg = error_msg or "Failed to create channel canvas"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
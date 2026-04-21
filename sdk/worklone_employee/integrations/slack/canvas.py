from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackCanvasTool(BaseTool):
    name = "slack_canvas"
    description = "Create and share Slack canvases in channels. Canvases are collaborative documents within Slack."
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
                    "description": "Slack channel ID (e.g., C1234567890)",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the canvas",
                },
                "content": {
                    "type": "string",
                    "description": "Canvas content in markdown format",
                },
                "document_content": {
                    "type": "object",
                    "description": "Structured canvas document content",
                },
            },
            "required": ["channel", "title", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/canvases.create"
        
        document_content = parameters.get("document_content")
        if document_content:
            body = {
                "title": parameters["title"],
                "channel_id": parameters["channel"],
                "document_content": document_content,
            }
        else:
            body = {
                "title": parameters["title"],
                "channel_id": parameters["channel"],
                "document_content": {
                    "type": "markdown",
                    "markdown": parameters["content"],
                },
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("ok", False):
                    return ToolResult(
                        success=False,
                        output="",
                        error=data.get("error", "Unknown error")
                    )
                    
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
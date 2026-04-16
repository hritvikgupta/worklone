from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackGetChannelInfoTool(BaseTool):
    name = "slack_get_channel_info"
    description = "Get detailed information about a Slack channel by its ID"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="Slack OAuth access token or bot token",
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
                    "description": "Channel ID to get information about (e.g., C1234567890)",
                },
                "include_num_members": {
                    "type": "boolean",
                    "description": "Whether to include the member count in the response",
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
        
        channel = parameters["channel"].strip()
        include_num_members = parameters.get("include_num_members", True)
        url = "https://slack.com/api/conversations.info"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params={
                        "channel": channel,
                        "include_num_members": include_num_members,
                    },
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackMessageReaderTool(BaseTool):
    name = "slack_message_reader"
    description = "Read the latest messages from Slack channels. Retrieve conversation history with filtering options."
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
            context_token_keys=("provider_token",),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "destinationType": {
                    "type": "string",
                    "description": "Destination type: channel or dm",
                },
                "channel": {
                    "type": "string",
                    "description": "Slack channel ID to read messages from (e.g., C1234567890)",
                },
                "dmUserId": {
                    "type": "string",
                    "description": "Slack user ID for DM conversation (e.g., U1234567890)",
                },
                "limit": {
                    "type": "number",
                    "description": "Number of messages to retrieve (default: 10, max: 15)",
                },
                "oldest": {
                    "type": "string",
                    "description": "Start of time range (timestamp)",
                },
                "latest": {
                    "type": "string",
                    "description": "End of time range (timestamp)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        destination_type = parameters.get("destinationType")
        is_dm = destination_type == "dm"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if is_dm:
                    dm_user_id = parameters.get("dmUserId")
                    if not dm_user_id:
                        return ToolResult(
                            success=False, output="", error="dmUserId is required when destinationType is 'dm'"
                        )
                    open_data = {"users": dm_user_id}
                    resp = await client.post(
                        "https://slack.com/api/conversations.open", headers=headers, data=open_data
                    )
                    if resp.status_code != 200:
                        return ToolResult(success=False, output="", error=resp.text)
                    try:
                        open_json = resp.json()
                    except:
                        return ToolResult(success=False, output="", error="Invalid response from Slack")
                    if not open_json.get("ok"):
                        return ToolResult(
                            success=False,
                            output="",
                            error=open_json.get("error", "Failed to open conversation"),
                        )
                    channel_id = open_json["channel"]["id"]
                else:
                    channel_id = parameters.get("channel")
                    if not channel_id:
                        return ToolResult(
                            success=False,
                            output="",
                            error="channel is required when destinationType is not 'dm'",
                        )
            
                limit_raw = parameters.get("limit")
                try:
                    limit = int(limit_raw) if limit_raw is not None else 10
                    limit = max(1, min(15, limit))
                except (ValueError, TypeError):
                    limit = 10
            
                history_data = {
                    "channel": channel_id,
                    "limit": limit,
                }
                oldest = parameters.get("oldest")
                if oldest:
                    history_data["oldest"] = oldest
                latest = parameters.get("latest")
                if latest:
                    history_data["latest"] = latest
            
                resp = await client.post(
                    "https://slack.com/api/conversations.history", headers=headers, data=history_data
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, output="", error=resp.text)
                try:
                    history_json = resp.json()
                except:
                    return ToolResult(success=False, output="", error="Invalid response from Slack")
                if history_json.get("ok"):
                    return ToolResult(success=True, output=resp.text, data=history_json)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=history_json.get("error", "Failed to read messages"),
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
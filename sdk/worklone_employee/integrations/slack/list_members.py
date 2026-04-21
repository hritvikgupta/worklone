from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackListMembersTool(BaseTool):
    name = "slack_list_members"
    description = "List all members (user IDs) in a Slack channel. Use with Get User Info to resolve IDs to names."
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
                    "description": "Channel ID to list members from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of members to return (default: 100, max: 200)",
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
        
        channel = parameters["channel"]
        limit = parameters.get("limit")
        if limit is not None:
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = 100
            limit = min(limit, 200)
        else:
            limit = 100
        
        url = "https://slack.com/api/conversations.members"
        params = {
            "channel": channel,
            "limit": limit,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception:
                        return ToolResult(success=False, output="", error="Invalid JSON response from Slack API")
                    
                    if data.get("ok"):
                        members = data.get("members", [])
                        result = {
                            "members": members,
                            "count": len(members),
                        }
                        return ToolResult(success=True, output=str(result), data=result)
                    else:
                        error = data.get("error", "Unknown error")
                        if error == "channel_not_found":
                            err_msg = "Channel not found. Please check the channel ID and try again."
                        elif error == "missing_scope":
                            err_msg = "Missing required permissions. Please reconnect your Slack account with the necessary scopes (channels:read, groups:read)."
                        elif error == "invalid_auth":
                            err_msg = "Invalid authentication. Please check your Slack credentials."
                        else:
                            err_msg = error or "Failed to list channel members from Slack"
                        return ToolResult(success=False, output="", error=err_msg)
                else:
                    return ToolResult(success=False, output="", error=f"HTTP {response.status_code}: {response.text}")
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
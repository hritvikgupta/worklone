from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackGetUserPresenceTool(BaseTool):
    name = "Slack Get User Presence"
    description = "Check whether a Slack user is currently active or away"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="Slack access token or bot token",
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
                "userId": {
                    "type": "string",
                    "description": "User ID to check presence for (e.g., U1234567890)",
                },
            },
            "required": ["userId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        user_id = parameters["userId"].strip()
        url = f"https://slack.com/api/users.getPresence?user={user_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                data = response.json()
                
                if not data.get("ok", False):
                    error = data.get("error", "Unknown Slack API error")
                    if error == "user_not_found":
                        error = "User not found. Please check the user ID and try again."
                    elif error == "missing_scope":
                        error = "Missing required permissions. Please reconnect your Slack account with the necessary scopes (users:read)."
                    else:
                        error = error or "Failed to get user presence from Slack"
                    return ToolResult(success=False, output="", error=error)
                
                output_data = {
                    "presence": data.get("presence"),
                    "online": data.get("online"),
                    "autoAway": data.get("auto_away"),
                    "manualAway": data.get("manual_away"),
                    "connectionCount": data.get("connection_count"),
                    "lastActivity": data.get("last_activity"),
                }
                return ToolResult(success=True, output=str(output_data), data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
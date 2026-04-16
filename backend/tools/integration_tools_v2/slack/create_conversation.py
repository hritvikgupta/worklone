from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackCreateConversationTool(BaseTool):
    name = "slack_create_conversation"
    description = "Create a new public or private channel in a Slack workspace."
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

    def _get_slack_error_message(self, error: str | None) -> str:
        if not error:
            return "Failed to create conversation in Slack"
        if error == "name_taken":
            return "A channel with this name already exists in the workspace."
        if error in ("invalid_name", "invalid_name_specials", "invalid_name_maxlength"):
            return "Invalid channel name. Use only lowercase letters, numbers, hyphens, and underscores (max 80 characters)."
        if error == "missing_scope":
            return "Missing required permissions. Please reconnect your Slack account with the necessary scopes (channels:manage, groups:write)."
        if error == "invalid_auth":
            return "Invalid authentication. Please check your Slack credentials."
        if error == "restricted_action":
            return "Workspace policy prevents channel creation."
        return error

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the channel to create (lowercase, numbers, hyphens, underscores only; max 80 characters)",
                },
                "isPrivate": {
                    "type": "boolean",
                    "description": "Create a private channel instead of a public one (default: false)",
                },
                "teamId": {
                    "type": "string",
                    "description": "Encoded team ID to create the channel in (required if using an org token)",
                },
            },
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/conversations.create"
        
        name = (parameters.get("name") or "").strip()
        if not name:
            return ToolResult(success=False, output="", error="Channel name is required.")
        
        body: dict = {
            "name": name,
        }
        
        is_private = parameters.get("isPrivate")
        if is_private is not None:
            body["is_private"] = bool(is_private)
        
        team_id = (parameters.get("teamId") or "").strip()
        if team_id:
            body["team_id"] = team_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output=response.text, error="Invalid JSON response from Slack API")
                
                if not data.get("ok"):
                    error_msg = self._get_slack_error_message(data.get("error"))
                    return ToolResult(success=False, output="", error=error_msg)
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
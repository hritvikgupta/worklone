from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackInviteToConversationTool(BaseTool):
    name = "slack_invite_to_conversation"
    description = "Invite one or more users to a Slack channel. Supports up to 100 users at a time."
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
            context_token_keys=("access_token",),
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
                    "description": "The ID of the channel to invite users to",
                },
                "users": {
                    "type": "string",
                    "description": "Comma-separated list of user IDs to invite (up to 100)",
                },
                "force": {
                    "type": "boolean",
                    "description": "When true, continues inviting valid users while skipping invalid ones (default: false)",
                },
            },
            "required": ["channel", "users"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        channel = (parameters.get("channel") or "").strip()
        users = (parameters.get("users") or "").strip()
        if not channel or not users:
            return ToolResult(success=False, output="", error="Channel ID and users are required.")
        
        body = {
            "channel": channel,
            "users": users,
        }
        force = parameters.get("force")
        if force is not None:
            body["force"] = force
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/conversations.invite"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if not (200 <= response.status_code < 300):
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("ok"):
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error = data.get("error", "Failed to invite users to Slack conversation")
                    mapped_errors = {
                        "channel_not_found": "Channel not found. Please verify the channel ID.",
                        "user_not_found": "One or more user IDs were not found.",
                        "cant_invite_self": "You cannot invite yourself to a channel.",
                        "already_in_channel": "One or more users are already in the channel.",
                        "is_archived": "The channel is archived and cannot accept new members.",
                        "not_in_channel": "The authenticated user is not a member of this channel.",
                        "cant_invite": "This user cannot be invited to the channel.",
                        "no_permission": "You do not have permission to invite this user to the channel.",
                        "org_user_not_in_team": "One or more invited members are in the Enterprise org but not this workspace.",
                        "missing_scope": "Missing required permissions. Please reconnect your Slack account with the necessary scopes (channels:manage, groups:write).",
                        "invalid_auth": "Invalid authentication. Please check your Slack credentials.",
                    }
                    error_msg = mapped_errors.get(error, error)
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackListUsersTool(BaseTool):
    name = "slack_list_users"
    description = "List all users in a Slack workspace. Returns user profiles with names and avatars."
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
                "includeDeleted": {
                    "type": "boolean",
                    "description": "Include deactivated/deleted users (default: false)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of users to return (default: 100, max: 200)",
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
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/users.list"
        
        limit_val = parameters.get("limit")
        if limit_val is not None:
            limit = min(int(float(limit_val)), 200)
        else:
            limit = 100
        
        include_deleted = bool(parameters.get("includeDeleted", False))
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params={"limit": limit},
                )
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("ok", False):
                    error = data.get("error", "Failed to list users from Slack")
                    if error == "missing_scope":
                        error = "Missing required permissions. Please reconnect your Slack account with the necessary scopes (users:read)."
                    elif error == "invalid_auth":
                        error = "Invalid authentication. Please check your Slack credentials."
                    return ToolResult(success=False, output="", error=error)
                
                members = data.get("members", [])
                users = []
                for user in members:
                    if user.get("id") == "USLACKBOT":
                        continue
                    if not include_deleted and user.get("deleted"):
                        continue
                    profile = user.get("profile", {})
                    real_name = user.get("real_name") or profile.get("real_name", "")
                    avatar = profile.get("image_72") or profile.get("image_48", "")
                    user_out = {
                        "id": user.get("id"),
                        "name": user.get("name"),
                        "real_name": real_name,
                        "display_name": profile.get("display_name", ""),
                        "email": profile.get("email", ""),
                        "is_bot": user.get("is_bot", False),
                        "is_admin": user.get("is_admin", False),
                        "is_owner": user.get("is_owner", False),
                        "deleted": user.get("deleted", False),
                        "timezone": user.get("tz"),
                        "avatar": avatar,
                        "status_text": profile.get("status_text", ""),
                        "status_emoji": profile.get("status_emoji", ""),
                    }
                    users.append(user_out)
                
                ids_list = [u["id"] for u in users]
                names_list = [u["name"] for u in users]
                output_data = {
                    "users": users,
                    "ids": ids_list,
                    "names": names_list,
                    "count": len(users),
                }
                return ToolResult(success=True, output=str(output_data), data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
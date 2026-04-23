from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XManageFollowTool(BaseTool):
    name = "x_manage_follow"
    description = "Follow or unfollow a user on X"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="X_ACCESS_TOKEN",
                description="X OAuth access token",
                env_var="X_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "x",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("X_ACCESS_TOKEN",),
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
                    "description": "The authenticated user ID",
                },
                "targetUserId": {
                    "type": "string",
                    "description": "The user ID to follow or unfollow",
                },
                "action": {
                    "type": "string",
                    "description": 'Action to perform: "follow" or "unfollow"',
                },
            },
            "required": ["userId", "targetUserId", "action"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        user_id = parameters.get("userId", "").strip()
        target_user_id = parameters.get("targetUserId", "").strip()
        action = parameters.get("action", "")
        
        url = "https://api.x.com/2/users/{}/following".format(user_id)
        json_body = None
        
        if action == "unfollow":
            url = "https://api.x.com/2/users/{}/following/{}".format(user_id, target_user_id)
        else:
            json_body = {"target_user_id": target_user_id}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if action == "unfollow":
                    response = await client.delete(url, headers=headers)
                else:
                    response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        if not data.get("data"):
                            errors = data.get("errors", [])
                            error_msg = errors[0].get("detail") if errors else "Failed to manage follow"
                            return ToolResult(success=False, output="", error=error_msg)
                        
                        output_data = {
                            "following": data["data"].get("following", False),
                            "pendingFollow": data["data"].get("pending_follow", False),
                        }
                        return ToolResult(success=True, output=str(output_data), data=output_data)
                    except Exception:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
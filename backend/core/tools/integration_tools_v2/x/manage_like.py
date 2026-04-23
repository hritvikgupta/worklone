from typing import Any
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XManageLikeTool(BaseTool):
    name = "x_manage_like"
    description = "Like or unlike a tweet on X"
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
                "tweetId": {
                    "type": "string",
                    "description": "The tweet ID to like or unlike",
                },
                "action": {
                    "type": "string",
                    "description": 'Action to perform: "like" or "unlike"',
                },
            },
            "required": ["userId", "tweetId", "action"],
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
        tweet_id = parameters["tweetId"].strip()
        action = parameters["action"]
        
        if action == "unlike":
            url = f"https://api.x.com/2/users/{user_id}/likes/{tweet_id}"
            http_method = "DELETE"
            body = None
        else:
            url = f"https://api.x.com/2/users/{user_id}/likes"
            http_method = "POST"
            body = {"tweet_id": tweet_id}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if http_method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                json_data = response.json()
                
                if not json_data.get("data"):
                    errors = json_data.get("errors", [])
                    error_detail = errors[0].get("detail") if errors else "Failed to manage like"
                    return ToolResult(
                        success=False,
                        output={"liked": False},
                        error=error_detail,
                    )
                
                liked = json_data["data"].get("liked", False)
                return ToolResult(success=True, output={"liked": liked})
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
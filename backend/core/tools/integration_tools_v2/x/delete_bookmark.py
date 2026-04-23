from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XDeleteBookmarkTool(BaseTool):
    name = "x_delete_bookmark"
    description = "Remove a tweet from the authenticated user's bookmarks"
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
                    "description": "The tweet ID to remove from bookmarks",
                },
            },
            "required": ["userId", "tweetId"],
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
        url = f"https://api.x.com/2/users/{user_id}/bookmarks/{tweet_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if not data.get("data"):
                        error_detail = data.get("errors", [{}])[0].get("detail", "Failed to remove bookmark")
                        return ToolResult(
                            success=False,
                            output="",
                            error=error_detail,
                            data={"bookmarked": False},
                        )
                    bookmarked = data["data"].get("bookmarked", False)
                    return ToolResult(
                        success=True,
                        output=response.text,
                        data={"bookmarked": bookmarked},
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
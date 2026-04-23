from typing import Dict
import httpx
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetMeTool(BaseTool):
    name = "x_get_me"
    description = "Get the authenticated user's profile information"
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
            context_token_keys=("provider_token",),
            env_token_keys=("X_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
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
        
        query_params = {
            "user.fields": "created_at,description,profile_image_url,verified,public_metrics,location,url",
        }
        query_string = urlencode(query_params)
        url = f"https://api.x.com/2/users/me?{query_string}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("data"):
                    error_msg = data.get("errors", [{}])[0].get("detail", "Failed to get authenticated user info")
                    return ToolResult(success=False, output="", error=error_msg)
                
                user_data = data["data"]
                transformed_user = {
                    "id": user_data["id"],
                    "username": user_data["username"],
                    "name": user_data["name"],
                    "description": user_data.get("description"),
                    "profileImageUrl": user_data.get("profile_image_url"),
                    "verified": user_data["verified"],
                    "metrics": {
                        "followersCount": user_data["public_metrics"]["followers_count"],
                        "followingCount": user_data["public_metrics"]["following_count"],
                        "tweetCount": user_data["public_metrics"]["tweet_count"],
                    },
                }
                output_data = {"user": transformed_user}
                output_str = json.dumps(output_data)
                
                return ToolResult(success=True, output=output_str, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetFollowingTool(BaseTool):
    name = "x_get_following"
    description = "Get the list of users that a user is following"
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

    def _transform_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        public_metrics = user.get("public_metrics", {})
        return {
            "id": user["id"],
            "username": user["username"],
            "name": user["name"],
            "description": user.get("description"),
            "profileImageUrl": user.get("profile_image_url"),
            "verified": user.get("verified", False),
            "metrics": {
                "followersCount": public_metrics.get("followers_count", 0),
                "followingCount": public_metrics.get("following_count", 0),
                "tweetCount": public_metrics.get("tweet_count", 0),
            },
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": "The user ID whose following list to retrieve",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results (1-1000, default 100)",
                },
                "paginationToken": {
                    "type": "string",
                    "description": "Pagination token for next page",
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
        query_params: Dict[str, str] = {
            "user.fields": "created_at,description,profile_image_url,verified,public_metrics,location",
        }
        
        if "maxResults" in parameters:
            try:
                max_results = int(parameters["maxResults"])
                query_params["max_results"] = str(max(1, min(1000, max_results)))
            except (ValueError, TypeError):
                pass
        
        if "paginationToken" in parameters and parameters["paginationToken"]:
            query_params["pagination_token"] = parameters["paginationToken"]
        
        url = f"https://api.x.com/2/users/{user_id}/following"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if not data.get("data") or not isinstance(data["data"], list):
                            errors = data.get("errors", [{}])
                            error_msg = errors[0].get("detail", "No following data found or invalid response") if errors else "No following data found or invalid response"
                            return ToolResult(success=False, output="", error=error_msg)
                        
                        users = [self._transform_user(user) for user in data["data"]]
                        meta = {
                            "resultCount": data.get("meta", {}).get("result_count", len(users)),
                            "nextToken": data.get("meta", {}).get("next_token"),
                        }
                        output_data = {
                            "users": users,
                            "meta": meta,
                        }
                        return ToolResult(success=True, output=response.text, data=output_data)
                    except Exception as parse_e:
                        return ToolResult(success=False, output="", error=f"Failed to parse response: {str(parse_e)}")
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
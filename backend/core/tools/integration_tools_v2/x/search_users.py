from typing import Any, Dict, List
import httpx
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XSearchUsersTool(BaseTool):
    name = "x_search_users"
    description = "Search for X users by name, username, or bio"
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
            context_token_keys=("x_token",),
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
                "query": {
                    "type": "string",
                    "description": "Search keyword (1-50 chars, matches name, username, or bio)",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results (1-1000, default 100)",
                },
                "nextToken": {
                    "type": "string",
                    "description": "Pagination token for next page",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            empty_output = {"users": [], "meta": {"resultCount": 0, "nextToken": None}}
            return ToolResult(
                success=False,
                output=json.dumps(empty_output),
                data=empty_output,
                error="Access token not configured.",
            )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        query_params: Dict[str, str] = {
            "query": parameters["query"],
            "user.fields": "created_at,description,profile_image_url,verified,public_metrics,location",
        }

        if parameters.get("maxResults") is not None:
            try:
                max_r = max(1, min(1000, int(parameters["maxResults"])))
                query_params["max_results"] = str(max_r)
            except (ValueError, TypeError):
                pass

        if parameters.get("nextToken"):
            query_params["next_token"] = parameters["nextToken"]

        url = f"https://api.x.com/2/users/search?{urlencode(query_params)}"

        empty_output = {"users": [], "meta": {"resultCount": 0, "nextToken": None}}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code not in [200]:
                    return ToolResult(
                        success=False,
                        output=json.dumps(empty_output),
                        data=empty_output,
                        error=response.text,
                    )

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    return ToolResult(
                        success=False,
                        output=json.dumps(empty_output),
                        data=empty_output,
                        error="Invalid JSON response",
                    )

                if not data.get("data") or not isinstance(data["data"], list):
                    errors = data.get("errors", [])
                    error_msg = (
                        errors[0].get("detail") if errors else "No users found or invalid response"
                    )
                    return ToolResult(
                        success=False,
                        output=json.dumps(empty_output),
                        data=empty_output,
                        error=error_msg,
                    )

                users = [self._transform_user(user) for user in data["data"]]
                meta = {
                    "resultCount": data.get("meta", {}).get("result_count", len(users)),
                    "nextToken": data.get("meta", {}).get("next_token"),
                }
                output_data = {"users": users, "meta": meta}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data, indent=2),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output=json.dumps(empty_output),
                data=empty_output,
                error=f"API error: {str(e)}",
            )
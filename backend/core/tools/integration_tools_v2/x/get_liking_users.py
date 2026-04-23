from typing import Any, Dict
import httpx
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetLikingUsersTool(BaseTool):
    name = "x_get_liking_users"
    description = "Get the list of users who liked a specific tweet"
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
            context_token_keys=("access_token",),
            env_token_keys=("X_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tweetId": {
                    "type": "string",
                    "description": "The tweet ID to get liking users for",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results (1-100, default 100)",
                },
                "paginationToken": {
                    "type": "string",
                    "description": "Pagination token for next page",
                },
            },
            "required": ["tweetId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        tweet_id = parameters["tweetId"].strip()
        if not tweet_id:
            return ToolResult(success=False, output="", error="Invalid tweet ID.")

        query_params: Dict[str, str] = {
            "user.fields": "created_at,description,profile_image_url,verified,public_metrics",
        }

        if "maxResults" in parameters:
            try:
                max_results = max(1, min(100, int(float(parameters["maxResults"]))))
                query_params["max_results"] = str(max_results)
            except ValueError:
                pass

        pagination_token = parameters.get("paginationToken")
        if pagination_token:
            query_params["pagination_token"] = pagination_token

        query_string = urlencode(query_params)
        url = f"https://api.x.com/2/tweets/{tweet_id}/liking_users?{query_string}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    if not isinstance(data.get("data"), list):
                        error_detail = ""
                        if "errors" in data and data["errors"]:
                            error_detail = data["errors"][0].get("detail", "")
                        error_msg = error_detail or "No liking users found or invalid response"
                        return ToolResult(success=False, output="", error=error_msg)

                    users = []
                    for user_raw in data["data"]:
                        user = {
                            "id": user_raw["id"],
                            "username": user_raw["username"],
                            "name": user_raw["name"],
                            "description": user_raw.get("description"),
                            "profileImageUrl": user_raw.get("profile_image_url"),
                            "verified": user_raw.get("verified", False),
                            "metrics": {
                                "followersCount": user_raw["public_metrics"]["followers_count"],
                                "followingCount": user_raw["public_metrics"]["following_count"],
                                "tweetCount": user_raw["public_metrics"]["tweet_count"],
                            },
                        }
                        users.append(user)

                    meta = {
                        "resultCount": data.get("meta", {}).get("result_count", len(users)),
                        "nextToken": data.get("meta", {}).get("next_token"),
                    }

                    output_data = {
                        "users": users,
                        "meta": meta,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
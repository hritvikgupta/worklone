from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetBookmarksTool(BaseTool):
    name = "x_get_bookmarks"
    description = "Get bookmarked tweets for the authenticated user"
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
            "properties": {
                "userId": {
                    "type": "string",
                    "description": "The authenticated user ID",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results (1-100)",
                },
                "paginationToken": {
                    "type": "string",
                    "description": "Pagination token for next page of results",
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
        url = f"https://api.x.com/2/users/{user_id}/bookmarks"
        
        query_params: Dict[str, Any] = {
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys,attachments.poll_ids",
            "tweet.fields": "created_at,conversation_id,in_reply_to_user_id,attachments,context_annotations,public_metrics",
            "user.fields": "name,username,description,profile_image_url,verified,public_metrics",
        }
        
        if parameters.get("maxResults"):
            max_results = max(1, min(100, int(parameters["maxResults"])))
            query_params["max_results"] = max_results
        
        if parameters.get("paginationToken"):
            query_params["pagination_token"] = parameters["paginationToken"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not isinstance(data.get("data"), list):
                    errors = data.get("errors", [{}])
                    error_detail = errors[0].get("detail", "No bookmarks found or invalid response")
                    return ToolResult(success=False, output="", error=error_detail)
                
                tweets = []
                for tweet in data["data"]:
                    transformed_tweet = {
                        "id": tweet["id"],
                        "text": tweet["text"],
                        "createdAt": tweet["created_at"],
                        "authorId": tweet["author_id"],
                        "conversationId": tweet.get("conversation_id"),
                        "inReplyToUserId": tweet.get("in_reply_to_user_id"),
                        "publicMetrics": tweet.get("public_metrics"),
                    }
                    tweets.append(transformed_tweet)
                
                users = []
                includes = data.get("includes", {})
                if includes.get("users"):
                    for user in includes["users"]:
                        transformed_user = {
                            "id": user["id"],
                            "username": user["username"],
                            "name": user["name"],
                            "description": user.get("description"),
                            "profileImageUrl": user.get("profile_image_url"),
                            "verified": user.get("verified"),
                            "metrics": user.get("public_metrics"),
                        }
                        users.append(transformed_user)
                
                meta = data.get("meta", {})
                output_data = {
                    "tweets": tweets,
                    "includes": {
                        "users": users,
                    },
                    "meta": {
                        "resultCount": meta.get("result_count", 0),
                        "newestId": meta.get("newest_id"),
                        "oldestId": meta.get("oldest_id"),
                        "nextToken": meta.get("next_token"),
                        "previousToken": meta.get("previous_token"),
                    },
                }
                
                return ToolResult(success=True, output="", data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
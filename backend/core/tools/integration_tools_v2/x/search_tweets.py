from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XSearchTweetsTool(BaseTool):
    name = "x_search_tweets"
    description = "Search for recent tweets using keywords, hashtags, or advanced query operators"
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
                "query": {
                    "type": "string",
                    "description": 'Search query (supports operators like "from:", "to:", "#hashtag", "has:images", "is:retweet", "lang:")',
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results (10-100, default 10)",
                },
                "startTime": {
                    "type": "string",
                    "description": "Oldest UTC timestamp in ISO 8601 format (e.g., 2024-01-01T00:00:00Z)",
                },
                "endTime": {
                    "type": "string",
                    "description": "Newest UTC timestamp in ISO 8601 format",
                },
                "sinceId": {
                    "type": "string",
                    "description": "Returns tweets with ID greater than this",
                },
                "untilId": {
                    "type": "string",
                    "description": "Returns tweets with ID less than this",
                },
                "sortOrder": {
                    "type": "string",
                    "description": 'Sort order: "recency" or "relevancy"',
                },
                "nextToken": {
                    "type": "string",
                    "description": "Pagination token for next page of results",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        params: Dict[str, str] = {
            "query": parameters["query"],
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys,attachments.poll_ids",
            "tweet.fields": "created_at,conversation_id,in_reply_to_user_id,attachments,context_annotations,public_metrics",
            "user.fields": "name,username,description,profile_image_url,verified,public_metrics",
        }
        
        if "maxResults" in parameters:
            try:
                max_results = max(10, min(100, int(float(parameters["maxResults"]))))
                params["max_results"] = str(max_results)
            except (ValueError, TypeError):
                pass
        
        param_map = {
            "startTime": "start_time",
            "endTime": "end_time",
            "sinceId": "since_id",
            "untilId": "until_id",
            "sortOrder": "sort_order",
            "nextToken": "next_token",
        }
        for schema_key, api_key in param_map.items():
            value = parameters.get(schema_key)
            if value is not None and str(value).strip():
                params[api_key] = str(value)
        
        url = "https://api.x.com/2/tweets/search/recent"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XSearchTool(BaseTool):
    name = "x_search"
    description = "Search for tweets using keywords, hashtags, or advanced queries"
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
                "query": {
                    "type": "string",
                    "description": 'Search query (e.g., "AI news", "#technology", "from:username"). Supports X search operators',
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results to return (e.g., 10, 25, 50). Default: 10, max: 100",
                },
                "startTime": {
                    "type": "string",
                    "description": "Start time for search (ISO 8601 format)",
                },
                "endTime": {
                    "type": "string",
                    "description": "End time for search (ISO 8601 format)",
                },
                "sortOrder": {
                    "type": "string",
                    "description": "Sort order for results (recency or relevancy)",
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
        
        url = "https://api.twitter.com/2/tweets/search/recent"
        query_params: Dict[str, str] = {
            "query": parameters["query"],
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys,attachments.poll_ids",
            "tweet.fields": "created_at,conversation_id,in_reply_to_user_id,attachments,context_annotations,public_metrics",
            "user.fields": "name,username,description,profile_image_url,verified,public_metrics",
        }
        
        max_results = parameters.get("maxResults")
        if max_results is not None:
            try:
                mr = float(max_results)
                if mr < 10:
                    mr = 10.0
                query_params["max_results"] = str(int(mr))
            except ValueError:
                pass
        
        start_time = parameters.get("startTime")
        if start_time:
            query_params["start_time"] = start_time
        
        end_time = parameters.get("endTime")
        if end_time:
            query_params["end_time"] = end_time
        
        sort_order = parameters.get("sortOrder")
        if sort_order:
            query_params["sort_order"] = sort_order
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class XGetRetweetedByTool(BaseTool):
    name = "x_get_retweeted_by"
    description = "Get the list of users who retweeted a specific tweet"
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
                "tweetId": {
                    "type": "string",
                    "description": "The tweet ID to get retweeters for",
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
        query_params: Dict[str, str] = {
            "user.fields": "created_at,description,profile_image_url,verified,public_metrics",
        }
        max_results = parameters.get("maxResults")
        if max_results is not None:
            max_r = max(1, min(100, int(max_results)))
            query_params["max_results"] = str(max_r)
        pagination_token = parameters.get("paginationToken")
        if pagination_token:
            query_params["pagination_token"] = str(pagination_token)
        
        url = f"https://api.x.com/2/tweets/{tweet_id}/retweeted_by"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
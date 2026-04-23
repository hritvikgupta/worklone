from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class XGetQuoteTweetsTool(BaseTool):
    name = "x_get_quote_tweets"
    description = "Get tweets that quote a specific tweet"
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
                "tweetId": {
                    "type": "string",
                    "description": "The tweet ID to get quote tweets for",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results (10-100, default 10)",
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
        
        tweet_id = (parameters.get("tweetId") or "").strip()
        if not tweet_id:
            return ToolResult(success=False, output="", error="tweetId is required.")
        
        query_params: Dict[str, str] = {
            "expansions": "author_id,attachments.media_keys",
            "tweet.fields": "created_at,conversation_id,public_metrics,context_annotations",
            "user.fields": "name,username,description,profile_image_url,verified,public_metrics",
        }
        
        if "maxResults" in parameters:
            try:
                max_results = int(parameters["maxResults"])
                clamped = max(10, min(100, max_results))
                query_params["max_results"] = str(clamped)
            except (ValueError, TypeError):
                pass
        
        pagination_token = parameters.get("paginationToken")
        if pagination_token:
            query_params["pagination_token"] = str(pagination_token)
        
        url = f"https://api.x.com/2/tweets/{tweet_id}/quote_tweets"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if data.get("errors"):
                        error_detail = data["errors"][0].get("detail") if isinstance(data["errors"], list) and data["errors"] else "Unknown API error"
                        return ToolResult(success=False, output="", error=error_detail)
                    if not data.get("data") or not isinstance(data["data"], list):
                        error_detail = data.get("errors", [{}])[0].get("detail", "No quote tweets found or invalid response")
                        return ToolResult(success=False, output="", error=error_detail)
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
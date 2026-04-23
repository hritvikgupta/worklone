from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditSearchTool(BaseTool):
    name = "reddit_search"
    description = "Search for posts within a subreddit"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _normalize_subreddit(self, subreddit: str) -> str:
        return subreddit.lstrip("r/").strip().lower()

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="REDDIT_ACCESS_TOKEN",
                description="Access token for Reddit API",
                env_var="REDDIT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "reddit",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("REDDIT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subreddit": {
                    "type": "string",
                    "description": 'The subreddit to search in (e.g., "technology", "programming")',
                },
                "query": {
                    "type": "string",
                    "description": 'Search query text (e.g., "artificial intelligence", "machine learning tutorial")',
                },
                "sort": {
                    "type": "string",
                    "description": 'Sort method for search results (e.g., "relevance", "hot", "top", "new", "comments"). Default: "relevance"',
                },
                "time": {
                    "type": "string",
                    "description": 'Time filter for search results: "hour", "day", "week", "month", "year", or "all" (default: "all")',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of posts to return (e.g., 25). Default: 10, max: 100",
                },
                "restrict_sr": {
                    "type": "boolean",
                    "description": "Restrict search to the specified subreddit only (default: true)",
                },
                "after": {
                    "type": "string",
                    "description": "Fullname of a thing to fetch items after (for pagination)",
                },
                "before": {
                    "type": "string",
                    "description": "Fullname of a thing to fetch items before (for pagination)",
                },
                "count": {
                    "type": "number",
                    "description": "A count of items already seen in the listing (used for numbering)",
                },
                "show": {
                    "type": "string",
                    "description": 'Show items that would normally be filtered (e.g., "all")',
                },
                "type": {
                    "type": "string",
                    "description": '"link" (posts), "sr" (subreddits), or "user" (users). Default: "link"',
                },
                "sr_detail": {
                    "type": "boolean",
                    "description": "Expand subreddit details in the response",
                },
            },
            "required": ["subreddit", "query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "sim-studio/1.0 (https://github.com/simstudioai/sim)",
            "Accept": "application/json",
        }

        subreddit = self._normalize_subreddit(parameters["subreddit"])
        query = parameters["query"]
        sort = parameters.get("sort", "relevance")
        limit_raw = parameters.get("limit", 10)
        limit = min(max(1, int(float(limit_raw))), 100)
        restrict_sr_raw = parameters.get("restrict_sr")
        restrict_sr = restrict_sr_raw is not False

        params_dict: Dict[str, str] = {
            "q": query,
            "sort": sort,
            "limit": str(limit),
            "restrict_sr": "true" if restrict_sr else "false",
            "raw_json": "1",
        }

        time_ = parameters.get("time")
        if time_:
            params_dict["t"] = time_

        after = parameters.get("after")
        if after:
            params_dict["after"] = after

        before = parameters.get("before")
        if before:
            params_dict["before"] = before

        count_raw = parameters.get("count")
        if count_raw is not None:
            params_dict["count"] = str(int(float(count_raw)))

        show = parameters.get("show")
        if show:
            params_dict["show"] = show

        type_ = parameters.get("type")
        if type_:
            params_dict["type"] = type_

        sr_detail_raw = parameters.get("sr_detail")
        if sr_detail_raw is not None:
            params_dict["sr_detail"] = "1" if bool(sr_detail_raw) else "0"

        url = f"https://oauth.reddit.com/r/{subreddit}/search"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
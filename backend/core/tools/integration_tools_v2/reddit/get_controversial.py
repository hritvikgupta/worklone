from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditGetControversialTool(BaseTool):
    name = "reddit_get_controversial"
    description = "Fetch controversial posts from a subreddit"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _normalize_subreddit(self, subreddit: str) -> str:
        return subreddit.strip().lstrip("r/").rstrip("/").lower()

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
                    "description": 'The subreddit to fetch posts from (e.g., "technology", "news")',
                },
                "time": {
                    "type": "string",
                    "description": 'Time filter for controversial posts: "hour", "day", "week", "month", "year", or "all" (default: "all")',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of posts to return (e.g., 25). Default: 10, max: 100",
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
                "sr_detail": {
                    "type": "boolean",
                    "description": "Expand subreddit details in the response",
                },
            },
            "required": ["subreddit"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "sim-studio/1.0 (https://github.com/simstudioai/sim)",
            "Accept": "application/json",
        }

        subreddit = self._normalize_subreddit(parameters["subreddit"])
        limit = min(max(1, parameters.get("limit", 10)), 100)
        params_dict: Dict[str, str] = {
            "limit": str(limit),
            "raw_json": "1",
        }
        time_filter = parameters.get("time")
        if time_filter:
            params_dict["t"] = time_filter
        after = parameters.get("after")
        if after:
            params_dict["after"] = after
        before = parameters.get("before")
        if before:
            params_dict["before"] = before
        count = parameters.get("count")
        if count is not None:
            params_dict["count"] = str(count)
        show = parameters.get("show")
        if show:
            params_dict["show"] = show
        sr_detail = parameters.get("sr_detail")
        if sr_detail is not None:
            params_dict["sr_detail"] = str(bool(sr_detail)).lower()

        url = f"https://oauth.reddit.com/r/{subreddit}/controversial"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    children = data.get("data", {}).get("children", [])
                    subreddit_name = parameters.get("subreddit", "unknown")
                    if children and len(children) > 0:
                        first_post = children[0].get("data", {})
                        subreddit_name = first_post.get("subreddit", subreddit_name)
                    posts = []
                    for child in children:
                        post = child.get("data", {})
                        permalink = post.get("permalink", "")
                        posts.append({
                            "id": post.get("id", ""),
                            "name": post.get("name", ""),
                            "title": post.get("title", ""),
                            "author": post.get("author", "[deleted]"),
                            "url": post.get("url", ""),
                            "permalink": f"https://www.reddit.com{permalink}" if permalink else "",
                            "created_utc": post.get("created_utc", 0),
                            "score": post.get("score", 0),
                            "num_comments": post.get("num_comments", 0),
                            "is_self": bool(post.get("is_self", False)),
                            "selftext": post.get("selftext", ""),
                            "thumbnail": post.get("thumbnail", ""),
                            "subreddit": post.get("subreddit", subreddit_name),
                        })
                    transformed = {
                        "subreddit": subreddit_name,
                        "posts": posts,
                        "after": data.get("data", {}).get("after"),
                        "before": data.get("data", {}).get("before"),
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
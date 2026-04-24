from typing import Any, Dict, List
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditHotPostsTool(BaseTool):
    name = "reddit_hot_posts"
    description = "Fetch the most popular (hot) posts from a specified subreddit."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _normalize_subreddit(self, subreddit: str) -> str:
        s = subreddit.strip().lower()
        if s.startswith("r/"):
            return s[2:]
        if s.startswith("/r/"):
            return s[3:]
        return s

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
                    "description": 'The subreddit to fetch hot posts from (e.g., "technology", "news")',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of posts to return (e.g., 25). Default: 10, max: 100",
                },
            },
            "required": ["subreddit"],
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

        subreddit = parameters["subreddit"]
        limit = parameters.get("limit", 10)
        if isinstance(limit, (int, float)):
            limit = int(limit)
        limit = min(max(1, limit), 100)

        subreddit_norm = self._normalize_subreddit(subreddit)
        url = f"https://oauth.reddit.com/r/{subreddit_norm}/hot?limit={limit}&raw_json=1"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    posts: List[Dict[str, Any]] = []
                    children = data.get("data", {}).get("children", [])
                    for child in children:
                        post = child.get("data", {}) if isinstance(child, dict) else {}
                        author = post.get("author") or "[deleted]"
                        permalink = f"https://www.reddit.com{post.get('permalink', '')}" if post.get("permalink") else ""
                        thumbnail = post.get("thumbnail")
                        if thumbnail in ("self", "default"):
                            thumbnail = None
                        post_dict = {
                            "id": post.get("id", ""),
                            "name": post.get("name", ""),
                            "title": post.get("title", ""),
                            "author": author,
                            "url": post.get("url", ""),
                            "permalink": permalink,
                            "created_utc": post.get("created_utc", 0),
                            "score": post.get("score", 0),
                            "num_comments": post.get("num_comments", 0),
                            "selftext": post.get("selftext", ""),
                            "thumbnail": thumbnail,
                            "is_self": bool(post.get("is_self")),
                            "subreddit": post.get("subreddit", subreddit),
                        }
                        posts.append(post_dict)

                    subreddit_name = subreddit
                    if children:
                        first_child = children[0]
                        first_post = first_child.get("data", {}) if isinstance(first_child, dict) else {}
                        subreddit_name = first_post.get("subreddit") or subreddit

                    result = {
                        "subreddit": subreddit_name,
                        "posts": posts,
                        "after": data.get("data", {}).get("after"),
                        "before": data.get("data", {}).get("before"),
                    }
                    return ToolResult(success=True, output=response.text, data=result)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
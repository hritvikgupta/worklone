from typing import Any, Dict, List
import httpx
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class RedditGetCommentsTool(BaseTool):
    name = "reddit_get_comments"
    description = "Fetch comments from a specific Reddit post"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

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
            context_token_keys=("reddit_token",),
            env_token_keys=("REDDIT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _build_url(self, params: Dict[str, Any]) -> str:
        subreddit = params["subreddit"].strip().lower()
        post_id = params["postId"].strip()
        if not post_id or "/" in post_id or ".." in post_id:
            raise ValueError("Invalid postId")
        sort = params.get("sort", "confidence")
        limit = min(max(1, params.get("limit", 50)), 100)
        url_params: Dict[str, str] = {
            "sort": sort,
            "limit": str(limit),
            "raw_json": "1",
        }
        if params.get("depth") is not None:
            url_params["depth"] = str(int(params["depth"]))
        if params.get("context") is not None:
            url_params["context"] = str(int(params["context"]))
        if params.get("showedits") is not None:
            url_params["showedits"] = str(bool(params["showedits"]))
        if params.get("showmore") is not None:
            url_params["showmore"] = str(bool(params["showmore"]))
        if params.get("threaded") is not None:
            url_params["threaded"] = str(bool(params["threaded"]))
        if params.get("truncate") is not None:
            url_params["truncate"] = str(int(params["truncate"]))
        if params.get("comment"):
            url_params["comment"] = params["comment"]
        query_string = urlencode(url_params)
        return f"https://oauth.reddit.com/r/{subreddit}/comments/{post_id}?{query_string}"

    def _process_comments(self, comments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def recurse(comments_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            result: List[Dict[str, Any]] = []
            for comment in comments_list:
                comment_data = comment.get("data", {})
                if not comment_data or comment.get("kind") != "t1":
                    continue
                replies_data = comment_data.get("replies", {})
                replies_children = replies_data.get("data", {}).get("children", []) if replies_data else []
                replies = recurse(replies_children)
                permalink = comment_data.get("permalink")
                item: Dict[str, Any] = {
                    "id": comment_data.get("id", ""),
                    "name": comment_data.get("name", ""),
                    "author": comment_data.get("author", "[deleted]"),
                    "body": comment_data.get("body", ""),
                    "created_utc": comment_data.get("created_utc", 0),
                    "score": comment_data.get("score", 0),
                    "permalink": f"https://www.reddit.com{permalink}" if permalink else "",
                    "replies": replies,
                }
                result.append(item)
            return result
        return recurse(comments_data)

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "postId": {
                    "type": "string",
                    "description": 'The ID of the Reddit post to fetch comments from (e.g., "abc123")',
                },
                "subreddit": {
                    "type": "string",
                    "description": 'The subreddit where the post is located (e.g., "technology", "programming")',
                },
                "sort": {
                    "type": "string",
                    "description": 'Sort method for comments: "confidence", "top", "new", "controversial", "old", "random", "qa" (default: "confidence")',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of comments to return (e.g., 25). Default: 50, max: 100",
                },
                "depth": {
                    "type": "number",
                    "description": "Maximum depth of subtrees in the thread (controls nested comment levels)",
                },
                "context": {
                    "type": "number",
                    "description": "Number of parent comments to include",
                },
                "showedits": {
                    "type": "boolean",
                    "description": "Show edit information for comments",
                },
                "showmore": {
                    "type": "boolean",
                    "description": 'Include "load more comments" elements in the response',
                },
                "threaded": {
                    "type": "boolean",
                    "description": "Return comments in threaded/nested format",
                },
                "truncate": {
                    "type": "number",
                    "description": "Integer to truncate comment depth",
                },
                "comment": {
                    "type": "string",
                    "description": "ID36 of a comment to focus on (returns that comment thread)",
                },
            },
            "required": ["postId", "subreddit"],
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
        
        try:
            url = self._build_url(parameters)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                    
                    post_data = {}
                    if data and len(data) > 0 and data[0].get("data", {}).get("children"):
                        post_data = data[0]["data"]["children"][0]["data"]
                    
                    comments_data = []
                    if len(data) > 1 and data[1].get("data", {}).get("children"):
                        comments_data = data[1]["data"]["children"]
                    
                    comments = self._process_comments(comments_data)
                    
                    permalink = post_data.get("permalink")
                    output_data = {
                        "post": {
                            "id": post_data.get("id", ""),
                            "name": post_data.get("name", ""),
                            "title": post_data.get("title", ""),
                            "author": post_data.get("author", "[deleted]"),
                            "selftext": post_data.get("selftext", ""),
                            "created_utc": post_data.get("created_utc", 0),
                            "score": post_data.get("score", 0),
                            "permalink": f"https://www.reddit.com{permalink}" if permalink else "",
                        },
                        "comments": comments,
                    }
                    output_str = json.dumps(output_data)
                    return ToolResult(success=True, output=output_str, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
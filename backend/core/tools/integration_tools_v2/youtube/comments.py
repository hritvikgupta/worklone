from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class YouTubeCommentsTool(BaseTool):
    name = "youtube_comments"
    description = "Get top-level comments from a YouTube video with author details and engagement."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="provider_token",
                description="YouTube API Key",
                env_var="YOUTUBE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        return (context or {}).get("provider_token", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "videoId": {
                    "type": "string",
                    "description": "YouTube video ID (11-character string, e.g., \"dQw4w9WgXcQ\")",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of comments to return (1-100)",
                },
                "order": {
                    "type": "string",
                    "description": "Order of comments: \"time\" (newest first) or \"relevance\" (most relevant first)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token for pagination (from previous response nextPageToken)",
                },
            },
            "required": ["videoId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="YouTube API key not configured.")

        headers = {
            "Content-Type": "application/json",
        }

        url = "https://www.googleapis.com/youtube/v3/commentThreads"

        params = {
            "part": "snippet,replies",
            "videoId": parameters["videoId"],
            "key": api_key,
            "maxResults": parameters.get("maxResults", 20),
            "order": parameters.get("order", "relevance"),
        }
        page_token = parameters.get("pageToken")
        if page_token:
            params["pageToken"] = page_token

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if data.get("error"):
                        error_msg = data["error"].get("message", "Failed to fetch comments")
                        return ToolResult(success=False, output="", error=error_msg)

                    items = []
                    for item in data.get("items", []):
                        snippet = item.get("snippet", {})
                        top_level_comment = snippet.get("topLevelComment", {})
                        top_level_snippet = top_level_comment.get("snippet", {})
                        comment_id = top_level_comment.get("id") or item.get("id", "") or ""
                        items.append({
                            "commentId": comment_id,
                            "authorDisplayName": top_level_snippet.get("authorDisplayName", ""),
                            "authorChannelUrl": top_level_snippet.get("authorChannelUrl", ""),
                            "authorProfileImageUrl": top_level_snippet.get("authorProfileImageUrl", ""),
                            "textDisplay": top_level_snippet.get("textDisplay", ""),
                            "textOriginal": top_level_snippet.get("textOriginal", ""),
                            "likeCount": int(top_level_snippet.get("likeCount") or 0),
                            "publishedAt": top_level_snippet.get("publishedAt", ""),
                            "updatedAt": top_level_snippet.get("updatedAt", ""),
                            "replyCount": int(snippet.get("totalReplyCount") or 0),
                        })

                    transformed = {
                        "items": items,
                        "totalResults": data.get("pageInfo", {}).get("totalResults", len(items)),
                        "nextPageToken": data.get("nextPageToken"),
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
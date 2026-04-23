from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class YouTubeVideoDetailsTool(BaseTool):
    name = "youtube_video_details"
    description = "Get detailed information about a specific YouTube video including statistics, content details, live streaming info, and metadata."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="YOUTUBE_API_KEY",
                description="YouTube API Key",
                env_var="YOUTUBE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        if context is None:
            return ""
        api_key = context.get("YOUTUBE_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "videoId": {
                    "type": "string",
                    "description": "YouTube video ID (11-character string, e.g., \"dQw4w9WgXcQ\")",
                },
            },
            "required": ["videoId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Content-Type": "application/json",
        }

        url = "https://www.googleapis.com/youtube/v3/videos"
        query_params = {
            "part": "snippet,statistics,contentDetails,status,liveStreamingDetails",
            "id": parameters["videoId"],
            "key": api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if not data.get("items") or len(data["items"]) == 0:
                        return ToolResult(success=False, output="", error="Video not found")

                    item = data["items"][0]
                    snippet = item.get("snippet", {})
                    content_details = item.get("contentDetails", {})
                    statistics = item.get("statistics", {})
                    status = item.get("status", {})
                    live_details = item.get("liveStreamingDetails")

                    thumbnails = snippet.get("thumbnails", {})
                    thumbnail = (
                        thumbnails.get("high", {}).get("url")
                        or thumbnails.get("medium", {}).get("url")
                        or thumbnails.get("default", {}).get("url")
                        or ""
                    )

                    cv_str = live_details.get("concurrentViewers") if live_details else None
                    concurrent_viewers = int(cv_str) if cv_str else None

                    output_data = {
                        "videoId": item.get("id") or "",
                        "title": snippet.get("title") or "",
                        "description": snippet.get("description") or "",
                        "channelId": snippet.get("channelId") or "",
                        "channelTitle": snippet.get("channelTitle") or "",
                        "publishedAt": snippet.get("publishedAt") or "",
                        "duration": content_details.get("duration") or "",
                        "viewCount": int(statistics.get("viewCount") or 0),
                        "likeCount": int(statistics.get("likeCount") or 0),
                        "commentCount": int(statistics.get("commentCount") or 0),
                        "favoriteCount": int(statistics.get("favoriteCount") or 0),
                        "thumbnail": thumbnail,
                        "tags": snippet.get("tags", []),
                        "categoryId": snippet.get("categoryId"),
                        "definition": content_details.get("definition"),
                        "caption": content_details.get("caption"),
                        "licensedContent": content_details.get("licensedContent"),
                        "privacyStatus": status.get("privacyStatus"),
                        "liveBroadcastContent": snippet.get("liveBroadcastContent"),
                        "defaultLanguage": snippet.get("defaultLanguage"),
                        "defaultAudioLanguage": snippet.get("defaultAudioLanguage"),
                        "isLiveContent": live_details is not None,
                        "scheduledStartTime": live_details.get("scheduledStartTime") if live_details else None,
                        "actualStartTime": live_details.get("actualStartTime") if live_details else None,
                        "actualEndTime": live_details.get("actualEndTime") if live_details else None,
                        "concurrentViewers": concurrent_viewers,
                        "activeLiveChatId": live_details.get("activeLiveChatId") if live_details else None,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
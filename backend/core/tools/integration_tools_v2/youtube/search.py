from typing import Any, Dict
import httpx
import os
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class YouTubeSearchTool(BaseTool):
    name = "youtube_search"
    description = "Search for videos on YouTube using the YouTube Data API. Supports advanced filtering by channel, date range, duration, category, quality, captions, live streams, and more."
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

    def _resolve_api_key(self, context: Dict[str, Any] | None) -> str:
        api_key = context.get("YOUTUBE_API_KEY") if context else None
        if not api_key:
            api_key = os.getenv("YOUTUBE_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ""
        return api_key

    def _build_url(self, parameters: Dict[str, Any], api_key: str) -> str:
        query = parameters["query"]
        max_results = parameters.get("maxResults", 5)
        query_params: Dict[str, str] = {
            "part": "snippet",
            "type": "video",
            "key": api_key,
            "q": query,
            "maxResults": str(int(max_results)),
        }
        optional_params = [
            "pageToken",
            "channelId",
            "publishedAfter",
            "publishedBefore",
            "videoDuration",
            "order",
            "videoCategoryId",
            "videoDefinition",
            "videoCaption",
            "eventType",
            "regionCode",
            "relevanceLanguage",
            "safeSearch",
        ]
        for param_name in optional_params:
            value = parameters.get(param_name)
            if value:
                query_params[param_name] = str(value)
        return "https://www.googleapis.com/youtube/v3/search?" + urlencode(query_params)

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for YouTube videos",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of videos to return (1-50)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token for pagination (from previous response nextPageToken)",
                },
                "channelId": {
                    "type": "string",
                    "description": 'Filter results to a specific YouTube channel ID starting with "UC" (24-character string)',
                },
                "publishedAfter": {
                    "type": "string",
                    "description": 'Only return videos published after this date (RFC 3339 format: "2024-01-01T00:00:00Z")',
                },
                "publishedBefore": {
                    "type": "string",
                    "description": 'Only return videos published before this date (RFC 3339 format: "2024-01-01T00:00:00Z")',
                },
                "videoDuration": {
                    "type": "string",
                    "description": 'Filter by video length: "short" (<4 min), "medium" (4-20 min), "long" (>20 min), "any"',
                },
                "order": {
                    "type": "string",
                    "description": 'Sort results by: "date", "rating", "relevance" (default), "title", "videoCount", "viewCount"',
                },
                "videoCategoryId": {
                    "type": "string",
                    "description": 'Filter by YouTube category ID (e.g., "10" for Music, "20" for Gaming). Use video_categories to list IDs.',
                },
                "videoDefinition": {
                    "type": "string",
                    "description": 'Filter by video quality: "high" (HD), "standard", "any"',
                },
                "videoCaption": {
                    "type": "string",
                    "description": 'Filter by caption availability: "closedCaption" (has captions), "none" (no captions), "any"',
                },
                "eventType": {
                    "type": "string",
                    "description": 'Filter by live broadcast status: "live" (currently live), "upcoming" (scheduled), "completed" (past streams)',
                },
                "regionCode": {
                    "type": "string",
                    "description": 'Return results relevant to a specific region (ISO 3166-1 alpha-2 country code, e.g., "US", "GB")',
                },
                "relevanceLanguage": {
                    "type": "string",
                    "description": 'Return results most relevant to a language (ISO 639-1 code, e.g., "en", "es")',
                },
                "safeSearch": {
                    "type": "string",
                    "description": 'Content filtering level: "moderate" (default), "none", "strict"',
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any] | None = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="YouTube API key not configured.")

        headers = {
            "Content-Type": "application/json",
        }
        url = self._build_url(parameters, api_key)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")

                if data.get("error"):
                    error_info = data["error"]
                    error_msg = error_info.get("message") or str(error_info)
                    return ToolResult(success=False, output="", error=error_msg)

                return ToolResult(success=True, output=response.text, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
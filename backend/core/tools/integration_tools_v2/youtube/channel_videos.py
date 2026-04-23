from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class YouTubeChannelVideosTool(BaseTool):
    name = "youtube_channel_videos"
    description = "Search for videos from a specific YouTube channel with sorting options. For complete channel video list, use channel_info to get uploadsPlaylistId, then use playlist_items."
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "youtube",
            context=context,
            context_token_keys=("YOUTUBE_API_KEY",),
            env_token_keys=("YOUTUBE_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channelId": {
                    "type": "string",
                    "description": 'YouTube channel ID starting with "UC" (24-character string) to get videos from',
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of videos to return (1-50)",
                },
                "order": {
                    "type": "string",
                    "description": 'Sort order: "date" (newest first, default), "rating", "relevance", "title", "viewCount"',
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token for pagination (from previous response nextPageToken)",
                },
            },
            "required": ["channelId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        url = "https://www.googleapis.com/youtube/v3/search"
        params_dict = {
            "part": "snippet",
            "type": "video",
            "channelId": parameters["channelId"],
            "key": access_token,
            "maxResults": parameters.get("maxResults", 10),
            "order": parameters.get("order", "date"),
        }
        page_token = parameters.get("pageToken")
        if page_token:
            params_dict["pageToken"] = page_token
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code >= 400:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=True, output=response.text, data=None)
                
                if "error" in data:
                    error_msg = data["error"].get("message", "Failed to fetch channel videos")
                    return ToolResult(success=False, output="", error=error_msg)
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
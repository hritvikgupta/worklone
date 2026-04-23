from typing import Any, Dict
import httpx
import json
import os
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class YouTubeChannelInfoTool(BaseTool):
    name = "youtube_channel_info"
    description = "Get detailed information about a YouTube channel including statistics, branding, and content details."
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
        api_key = ""
        if context:
            api_key = (
                context.get("api_key")
                or context.get("YOUTUBE_API_KEY")
                or context.get("provider_token")
                or ""
            )
        if not api_key:
            api_key = os.getenv("YOUTUBE_API_KEY", "")
        return api_key

    def _build_output(self, item: Dict[str, Any]) -> Dict[str, Any]:
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})
        branding_settings = item.get("brandingSettings", {})
        image = branding_settings.get("image", {})
        thumbnails = snippet.get("thumbnails", {})
        thumbnail = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )
        return {
            "channelId": item.get("id") or "",
            "title": snippet.get("title") or "",
            "description": snippet.get("description") or "",
            "subscriberCount": int(statistics.get("subscriberCount") or 0),
            "videoCount": int(statistics.get("videoCount") or 0),
            "viewCount": int(statistics.get("viewCount") or 0),
            "publishedAt": snippet.get("publishedAt") or "",
            "thumbnail": thumbnail,
            "customUrl": snippet.get("customUrl"),
            "country": snippet.get("country"),
            "uploadsPlaylistId": content_details.get("relatedPlaylists", {}).get("uploads"),
            "bannerImageUrl": image.get("bannerExternalUrl"),
            "hiddenSubscriberCount": statistics.get("hiddenSubscriberCount", False),
        }

    def _transform_response(self, data: Dict[str, Any]) -> tuple[bool, Dict[str, Any], str]:
        items = data.get("items", [])
        if len(items) == 0:
            defaults = {
                "channelId": "",
                "title": "",
                "description": "",
                "subscriberCount": 0,
                "videoCount": 0,
                "viewCount": 0,
                "publishedAt": "",
                "thumbnail": "",
                "customUrl": None,
                "country": None,
                "uploadsPlaylistId": None,
                "bannerImageUrl": None,
                "hiddenSubscriberCount": False,
            }
            return False, defaults, "Channel not found"
        transformed = self._build_output(items[0])
        return True, transformed, ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channelId": {
                    "type": "string",
                    "description": "YouTube channel ID starting with \"UC\" (24-character string, use either channelId or username)",
                },
                "username": {
                    "type": "string",
                    "description": "YouTube channel username (use either channelId or username)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="YouTube API key not configured.")

        channel_id = parameters.get("channelId")
        username = parameters.get("username")
        if not channel_id and not username:
            return ToolResult(
                success=False,
                output="",
                error="Either channelId or username must be provided.",
            )

        url = "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics,contentDetails,brandingSettings"
        if channel_id:
            url += f"&id={urllib.parse.quote(channel_id)}"
        if username:
            url += f"&forUsername={urllib.parse.quote(username)}"
        url += f"&key={urllib.parse.quote(api_key)}"

        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    json_data: Dict[str, Any] = response.json()
                    success_flag, transformed, error_msg = self._transform_response(json_data)
                    return ToolResult(
                        success=success_flag,
                        output=json.dumps(transformed),
                        error=error_msg,
                        data=transformed,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
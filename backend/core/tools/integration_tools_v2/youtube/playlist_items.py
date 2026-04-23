from typing import Any, Dict, List
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class YouTubePlaylistItemsTool(BaseTool):
    name = "youtube_playlist_items"
    description = "Get videos from a YouTube playlist. Can be used with a channel uploads playlist to get all channel videos."
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
            "google",
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
                "playlistId": {
                    "type": "string",
                    "description": "YouTube playlist ID starting with \"PL\" or \"UU\" (34-character string). Use uploadsPlaylistId from channel_info to get all channel videos.",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of videos to return (1-50)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token for pagination (from previous response nextPageToken)",
                },
            },
            "required": ["playlistId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Content-Type": "application/json",
        }

        url = "https://www.googleapis.com/youtube/v3/playlistItems"

        params: Dict[str, Any] = {
            "part": "snippet,contentDetails",
            "playlistId": parameters["playlistId"],
            "key": access_token,
            "maxResults": parameters.get("maxResults", 10),
        }
        if "pageToken" in parameters:
            params["pageToken"] = parameters["pageToken"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if data.get("error"):
                        return ToolResult(
                            success=False,
                            output="",
                            error=data["error"].get("message", "Failed to fetch playlist items"),
                        )

                    items: List[Dict[str, Any]] = []
                    for index, item in enumerate(data.get("items", [])):
                        snippet = item.get("snippet", {})
                        content_details = item.get("contentDetails", {})
                        thumbnails = snippet.get("thumbnails", {})
                        items.append({
                            "videoId": content_details.get("videoId") or snippet.get("resourceId", {}).get("videoId", ""),
                            "title": snippet.get("title", ""),
                            "description": snippet.get("description", ""),
                            "thumbnail": (
                                thumbnails.get("medium", {}).get("url")
                                or thumbnails.get("default", {}).get("url")
                                or thumbnails.get("high", {}).get("url")
                                or ""
                            ),
                            "publishedAt": snippet.get("publishedAt", ""),
                            "channelTitle": snippet.get("channelTitle", ""),
                            "position": snippet.get("position", index),
                            "videoOwnerChannelId": snippet.get("videoOwnerChannelId"),
                            "videoOwnerChannelTitle": snippet.get("videoOwnerChannelTitle"),
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
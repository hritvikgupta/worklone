from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class YouTubeChannelPlaylistsTool(BaseTool):
    name = "youtube_channel_playlists"
    description = "Get all public playlists from a specific YouTube channel."
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
            context_token_keys=("provider_token",),
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
                    "description": "YouTube channel ID starting with \"UC\" (24-character string) to get playlists from",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of playlists to return (1-50)",
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
        
        url = "https://www.googleapis.com/youtube/v3/playlists"
        query_params = {
            "part": "snippet,contentDetails",
            "channelId": parameters["channelId"],
            "key": access_token,
            "maxResults": parameters.get("maxResults", 10),
        }
        if "pageToken" in parameters and parameters["pageToken"]:
            query_params["pageToken"] = parameters["pageToken"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
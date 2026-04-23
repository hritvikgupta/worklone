from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZoomListMeetingsTool(BaseTool):
    name = "zoom_list_meetings"
    description = "List all meetings for a Zoom user"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="zoom_access_token",
                description="Access token",
                env_var="ZOOM_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "zoom",
            context=context,
            context_token_keys=("zoom_access_token",),
            env_token_keys=("ZOOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": 'The user ID or email address (e.g., "me", "user@example.com", or "AbcDefGHi"). Use "me" for the authenticated user.'
                },
                "type": {
                    "type": "string",
                    "description": "Meeting type filter: scheduled, live, upcoming, upcoming_meetings, or previous_meetings"
                },
                "pageSize": {
                    "type": "number",
                    "description": "Number of records per page, 1-300 (e.g., 30, 50, 100)"
                },
                "nextPageToken": {
                    "type": "string",
                    "description": "Token for pagination to get next page of results"
                }
            },
            "required": ["userId"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        user_id = parameters["userId"]
        base_url = f"https://api.zoom.us/v2/users/{quote(user_id)}/meetings"
        params_dict = {
            "type": parameters.get("type"),
            "page_size": parameters.get("pageSize"),
            "next_page_token": parameters.get("nextPageToken"),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=params_dict)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error = response.text
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            error = error_data.get("message", error)
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
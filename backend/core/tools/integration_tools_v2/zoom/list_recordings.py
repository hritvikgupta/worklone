from typing import Any, Dict
import httpx
from urllib.parse import quote, urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZoomListRecordingsTool(BaseTool):
    name = "zoom_list_recordings"
    description = "List all cloud recordings for a Zoom user"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ZOOM_ACCESS_TOKEN",
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
            context_token_keys=("zoom_token",),
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
                "from": {
                    "type": "string",
                    "description": "Start date in yyyy-mm-dd format (within last 6 months)"
                },
                "to": {
                    "type": "string",
                    "description": "End date in yyyy-mm-dd format"
                },
                "pageSize": {
                    "type": "number",
                    "description": "Number of records per page, 1-300 (e.g., 30, 50, 100)"
                },
                "nextPageToken": {
                    "type": "string",
                    "description": "Token for pagination to get next page of results"
                },
                "trash": {
                    "type": "boolean",
                    "description": "Set to true to list recordings from trash"
                }
            },
            "required": ["userId"]
        }

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any] | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        user_id = parameters["userId"]
        base_url = f"https://api.zoom.us/v2/users/{quote(user_id)}/recordings"
        
        query_params: list[tuple[str, str]] = []
        from_date = parameters.get("from")
        if from_date:
            query_params.append(("from", from_date))
        to_date = parameters.get("to")
        if to_date:
            query_params.append(("to", to_date))
        page_size = parameters.get("pageSize")
        if page_size is not None:
            query_params.append(("page_size", str(page_size)))
        next_page_token = parameters.get("nextPageToken")
        if next_page_token:
            query_params.append(("next_page_token", next_page_token))
        trash = parameters.get("trash")
        if trash:
            query_params.append(("trash", "true"))
        
        query_string = urlencode(query_params)
        url = f"{base_url}?{query_string}" if query_string else base_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
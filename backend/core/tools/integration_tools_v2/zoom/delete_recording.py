from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZoomDeleteRecordingTool(BaseTool):
    name = "zoom_delete_recording"
    description = "Delete cloud recordings for a Zoom meeting"
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
            context_token_keys=("provider_token",),
            env_token_keys=("ZOOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "meetingId": {
                    "type": "string",
                    "description": 'The meeting ID or meeting UUID (e.g., "1234567890" or "4444AAABBBccccc12345==")',
                },
                "recordingId": {
                    "type": "string",
                    "description": "Specific recording file ID to delete. If not provided, deletes all recordings.",
                },
                "action": {
                    "type": "string",
                    "description": 'Delete action: "trash" (move to trash) or "delete" (permanently delete)',
                },
            },
            "required": ["meetingId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        meeting_id = parameters["meetingId"]
        url = f"https://api.zoom.us/v2/meetings/{quote(meeting_id)}/recordings"
        
        if recording_id := parameters.get("recordingId"):
            url += f"/{quote(recording_id)}"
        
        if action := parameters.get("action"):
            url += f"?action={quote(action)}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except:
                        data = {}
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except:
                        error_msg = f"Zoom API error: {response.status_code} {response.reason_phrase}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
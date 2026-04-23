from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZoomGetMeetingRecordingsTool(BaseTool):
    name = "zoom_get_meeting_recordings"
    description = "Get all recordings for a specific Zoom meeting"
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
                "includeFolderItems": {
                    "type": "boolean",
                    "description": "Include items within a folder",
                },
                "ttl": {
                    "type": "number",
                    "description": "Time to live for download URLs in seconds (max 604800)",
                },
                "downloadFiles": {
                    "type": "boolean",
                    "description": "Download recording files into file outputs",
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
        url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings"
        
        query_params: Dict[str, Any] = {}
        include_folder_items = parameters.get("includeFolderItems", False)
        if include_folder_items:
            query_params["recursive"] = True
        ttl = parameters.get("ttl")
        if ttl is not None:
            query_params["download_url_ttl"] = ttl
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200]:
                    json_data = response.json()
                    download_files = parameters.get("downloadFiles", False)
                    if download_files:
                        files_list: list[dict] = []
                        recording = json_data.get("recording", {})
                        
                        def extract_files(rec: dict):
                            for f in rec.get("recording_files", []):
                                files_list.append({
                                    "id": f.get("id"),
                                    "meeting_id": f.get("meeting_id"),
                                    "file_type": f.get("file_type"),
                                    "file_size": f.get("file_size"),
                                    "play_url": f.get("play_url"),
                                    "download_url": f.get("download_url"),
                                    "status": f.get("status"),
                                    "file_name": f.get("file_name"),
                                })
                            for folder in rec.get("recording_folders", []):
                                extract_files(folder)
                        
                        extract_files(recording)
                        json_data["files"] = files_list
                    
                    return ToolResult(success=True, output=response.text, data=json_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
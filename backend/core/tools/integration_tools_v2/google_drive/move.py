from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDriveMoveTool(BaseTool):
    name = "google_drive_move"
    description = "Move a file or folder to a different folder in Google Drive"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="OAuth access token for Google Drive",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("google_drive_token",),
            env_token_keys=("GOOGLE_DRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fileId": {
                    "type": "string",
                    "description": "The ID of the file or folder to move",
                },
                "destinationFolderId": {
                    "type": "string",
                    "description": "The ID of the destination folder",
                },
                "removeFromCurrent": {
                    "type": "boolean",
                    "description": "Whether to remove the file from its current parent folder (default: true). Set to false to add the file to the destination without removing it from the current location.",
                },
            },
            "required": ["fileId", "destinationFolderId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        file_id = (parameters.get("fileId") or "").strip()
        destination_folder_id = (parameters.get("destinationFolderId") or "").strip()
        remove_from_current = parameters.get("removeFromCurrent") is not False

        if not file_id:
            return ToolResult(success=False, output="", error="fileId is required")
        if not destination_folder_id:
            return ToolResult(success=False, output="", error="destinationFolderId is required")
        
        fields = "id,kind,name,mimeType,webViewLink,parents,createdTime,modifiedTime,owners,size"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                remove_parents = None
                if remove_from_current:
                    metadata_params = {
                        "fields": "parents",
                        "supportsAllDrives": "true",
                    }
                    metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
                    metadata_resp = await client.get(metadata_url, headers=headers, params=metadata_params)
                    
                    if metadata_resp.status_code >= 400:
                        try:
                            error_data = metadata_resp.json()
                            error_msg = error_data.get("error", {}).get("message", "Failed to retrieve file metadata")
                        except Exception:
                            error_msg = metadata_resp.text
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    metadata = metadata_resp.json()
                    parents = metadata.get("parents", [])
                    if parents:
                        remove_parents = ",".join(parents)
                
                move_params = {
                    "addParents": destination_folder_id,
                    "fields": fields,
                    "supportsAllDrives": "true",
                }
                if remove_parents:
                    move_params["removeParents"] = remove_parents
                
                move_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
                resp = await client.patch(
                    move_url,
                    headers=headers,
                    params=move_params,
                    json={},
                )
                
                if resp.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=resp.text, data=resp.json())
                else:
                    try:
                        data = resp.json()
                        error_msg = data.get("error", {}).get("message", "Failed to move Google Drive file")
                    except Exception:
                        error_msg = resp.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
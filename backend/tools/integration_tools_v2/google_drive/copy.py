from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDriveCopyTool(BaseTool):
    name = "google_drive_copy"
    description = "Create a copy of a file in Google Drive"
    category = "integration"
    ALL_FILE_FIELDS = "id,kind,name,mimeType,webViewLink,parents,createdTime,modifiedTime,owners,size"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="OAuth access token",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("access_token",),
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
                    "description": "The ID of the file to copy",
                },
                "newName": {
                    "type": "string",
                    "description": 'Name for the copied file (defaults to "Copy of [original name]")',
                },
                "destinationFolderId": {
                    "type": "string",
                    "description": "ID of the folder to place the copy in (defaults to same location as original)",
                },
            },
            "required": ["fileId"],
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
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/copy"
        
        query_params = {
            "fields": self.ALL_FILE_FIELDS,
            "supportsAllDrives": "true",
        }
        
        body: dict = {}
        if new_name := parameters.get("newName"):
            body["name"] = new_name
        if dest_folder_id := parameters.get("destinationFolderId"):
            body["parents"] = [dest_folder_id.strip()]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url, headers=headers, params=query_params, json=body
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleDriveCreateFolderTool(BaseTool):
    name = "google_drive_create_folder"
    description = "Create a new folder in Google Drive with complete metadata returned"
    category = "integration"

    ALL_FILE_FIELDS = (
        "id,kind,name,mimeType,description,owners,permissions,shared,ownedByMe,"
        "writersCanShare,viewersCanCopyContent,copyRequiresWriterPermission,"
        "sharingUser,starred,trashed,explicitlyTrashed,properties,appProperties,"
        "folderColorRgb,createdTime,modifiedTime,modifiedByMeTime,viewedByMeTime,"
        "sharedWithMeTime,lastModifyingUser,viewedByMe,modifiedByMe,webViewLink,"
        "iconLink,parents,spaces,driveId,capabilities,version,isAppAuthorized,"
        "contentRestrictions,linkShareMetadata"
    )

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Access token for Google Drive",
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
                "fileName": {
                    "type": "string",
                    "description": "Name of the folder to create",
                },
                "folderSelector": {
                    "type": "string",
                    "description": "Google Drive parent folder ID to create the folder in (e.g., 1ABCxyz...)",
                },
            },
            "required": ["fileName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        body: dict = {
            "name": parameters["fileName"],
            "mimeType": "application/vnd.google-apps.folder",
        }
        parent_folder_id = parameters.get("folderSelector")
        if parent_folder_id:
            body["parents"] = [parent_folder_id]

        url = "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201]:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except Exception:
                        pass
                    error_msg = error_data.get("error", {}).get("message", response.text)
                    return ToolResult(success=False, output="", error=error_msg)

                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response from API")

                folder_id = data.get("id")
                if not folder_id:
                    return ToolResult(success=False, output="", error="Failed to create folder: no ID returned")

                metadata_url = f"https://www.googleapis.com/drive/v3/files/{folder_id}?supportsAllDrives=true&fields={self.ALL_FILE_FIELDS}"
                metadata_headers = {
                    "Authorization": f"Bearer {access_token}",
                }
                metadata_response = await client.get(metadata_url, headers=metadata_headers)

                full_metadata = data
                if metadata_response.status_code == 200:
                    try:
                        full_metadata = metadata_response.json()
                    except Exception:
                        pass

                result_data = {"file": full_metadata}
                output_str = json.dumps(result_data)

                return ToolResult(success=True, output=output_str, data=result_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
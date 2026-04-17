from typing import Any, Dict
import httpx
import base64
import json
import time
from uuid import uuid4
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDriveUploadTool(BaseTool):
    name = "google_drive_upload"
    description = "Upload a file to Google Drive with complete metadata returned"
    category = "integration"

    GOOGLE_WORKSPACE_MIME_TYPES = [
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.google-apps.presentation",
    ]
    SOURCE_MIME_TYPES = {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
    }
    ALL_FILE_FIELDS = (
        "id,kind,name,mimeType,description,originalFilename,fullFileExtension,fileExtension,"
        "owners,permissions,permissionIds,shared,ownedByMe,writersCanShare,viewersCanCopyContent,"
        "copyRequiresWriterPermission,sharingUser,starred,trashed,explicitlyTrashed,properties,"
        "appProperties,createdTime,modifiedTime,modifiedByMeTime,viewedByMeTime,sharedWithMeTime,"
        "lastModifyingUser,viewedByMe,modifiedByMe,webViewLink,webContentLink,iconLink,"
        "thumbnailLink,exportLinks,size,quotaBytesUsed,md5Checksum,sha1Checksum,sha256Checksum,"
        "parents,spaces,driveId,capabilities,version,headRevisionId,hasThumbnail,thumbnailVersion,"
        "imageMediaMetadata,videoMediaMetadata,isAppAuthorized,contentRestrictions,linkShareMetadata"
    )

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Access token for the Google Drive API",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("GOOGLE_DRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    @staticmethod
    def _handle_sheets_format(content: str) -> tuple[str | None, int, int]:
        try:
            lines = [line.rstrip() for line in content.splitlines() if line.strip()]
            if not lines:
                return None, 0, 0
            rows = []
            for line in lines:
                if "\t" in line:
                    row = [field.strip() for field in line.split("\t")]
                else:
                    row = [field.strip() for field in line.split(",") if field.strip()]
                rows.append(row)
            row_count = len(rows)
            col_count = max((len(row) for row in rows), default=0)
            csv_lines = [",".join(row) for row in rows]
            csv_content = "\n".join(csv_lines)
            return csv_content, row_count, col_count
        except Exception:
            return None, 0, 0

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fileName": {
                    "type": "string",
                    "description": "The name of the file to upload",
                },
                "file": {
                    "type": "string",
                    "description": "Base64 encoded binary file to upload (use this OR content, not both)",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to upload (use this OR file, not both)",
                },
                "mimeType": {
                    "type": "string",
                    "description": "The MIME type of the file to upload (auto-detected if not provided)",
                },
                "folderSelector": {
                    "type": "string",
                    "description": "Google Drive folder ID to upload the file to (e.g., 1ABCxyz...)",
                },
                "folderId": {
                    "type": "string",
                    "description": "The ID of the folder to upload the file to (internal use)",
                },
            },
            "required": ["fileName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        file_name: str = parameters["fileName"]
        folder_id: str = parameters.get("folderSelector") or parameters.get("folderId", "")
        mime_type: str | None = parameters.get("mimeType")
        file_b64: str | None = parameters.get("file")
        content_str: str | None = parameters.get("content")

        if file_b64 is None and content_str is None:
            return ToolResult(
                success=False, output="", error="Must provide either 'file' (base64) or 'content'."
            )

        if file_b64 is not None and content_str is not None:
            return ToolResult(
                success=False,
                output="",
                error="Provide either 'file' or 'content', not both.",
            )

        is_file_upload = file_b64 is not None
        default_mime = "application/octet-stream" if is_file_upload else "text/plain"
        requested_mime_type = mime_type or default_mime

        try:
            if is_file_upload:
                file_buffer = base64.b64decode(file_b64)
            else:
                file_buffer = content_str.encode("utf-8")
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Failed to process file/content data: {str(e)}"
            )

        upload_mime_type = (
            self.SOURCE_MIME_TYPES.get(requested_mime_type, requested_mime_type)
            if requested_mime_type in self.GOOGLE_WORKSPACE_MIME_TYPES
            else requested_mime_type
        )

        if requested_mime_type == "application/vnd.google-apps.spreadsheet":
            try:
                text_content = file_buffer.decode("utf-8", errors="ignore")
                csv_content, _, _ = self._handle_sheets_format(text_content)
                if csv_content is not None:
                    file_buffer = csv_content.encode("utf-8")
                    upload_mime_type = "text/csv"
            except Exception:
                pass  # Proceed with original buffer

        metadata = {"name": file_name, "mimeType": requested_mime_type}
        if folder_id and folder_id.strip():
            metadata["parents"] = [folder_id.strip()]

        boundary = f"boundary_{int(time.time() * 1000000)}_{uuid4().hex[:8]}"
        multipart_parts = [
            f"--{boundary}",
            "Content-Type: application/json; charset=UTF-8",
            "",
            json.dumps(metadata),
            f"--{boundary}",
            f"Content-Type: {upload_mime_type}",
            "Content-Transfer-Encoding: base64",
            "",
            base64.b64encode(file_buffer).decode("ascii"),
            f"--{boundary}--",
        ]
        multipart_body = "\r\n".join(multipart_parts)

        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, content=multipart_body)

                if response.status_code not in [200, 201]:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Upload failed: {response.status_code} {response.text}",
                    )

                data = response.json()
                file_id = data.get("id")
                if not file_id:
                    return ToolResult(
                        success=False, output="", error="No file ID returned from upload."
                    )

                # Update name for workspace types if needed
                if requested_mime_type in self.GOOGLE_WORKSPACE_MIME_TYPES:
                    update_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?supportsAllDrives=true"
                    update_headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    }
                    update_body = json.dumps({"name": file_name})
                    update_response = await client.patch(
                        update_url, headers=update_headers, content=update_body
                    )
                    # Ignore update errors, as upload succeeded

                # Fetch complete file metadata
                get_url = (
                    f"https://www.googleapis.com/drive/v3/files/{file_id}?"
                    f"supportsAllDrives=true&fields={self.ALL_FILE_FIELDS}"
                )
                get_headers = {"Authorization": f"Bearer {access_token}"}
                final_response = await client.get(get_url, headers=get_headers)

                if final_response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to fetch file metadata: {final_response.text}",
                    )

                final_file = final_response.json()

                return ToolResult(
                    success=True,
                    output=f"File uploaded successfully: {final_file.get('name', 'Unknown')} "
                           f"({final_file.get('webViewLink', '')})",
                    data={"file": final_file},
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
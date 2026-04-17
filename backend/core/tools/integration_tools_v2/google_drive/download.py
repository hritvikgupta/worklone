from typing import Any, Dict
import httpx
import base64
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDriveDownloadTool(BaseTool):
    name = "google_drive_download"
    description = "Download a file from Google Drive with complete metadata (exports Google Workspace files automatically)"
    category = "integration"

    GOOGLE_WORKSPACE_MIME_TYPES = [
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.google-apps.presentation",
        "application/vnd.google-apps.drawing",
        "application/vnd.google-apps.script",
        "application/vnd.google-apps.form",
    ]
    DEFAULT_EXPORT_FORMATS = {
        "application/vnd.google-apps.document": "application/pdf",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "application/pdf",
        "application/vnd.google-apps.drawing": "application/pdf",
        "application/vnd.google-apps.script": "text/plain",
        "application/vnd.google-apps.form": "text/html",
    }
    ALL_FILE_FIELDS = "*,capabilities(canReadRevisions)"
    ALL_REVISION_FIELDS = "id,kind,modifiedTime,lastModifyingUser,publishAuto,published,publishedOutsideDomain,lastModifyingUserName,size,md5Checksum"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Google Drive access token",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google",
            context=context,
            context_token_keys=("accessToken",),
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
                    "description": "The ID of the file to download",
                },
                "mimeType": {
                    "type": "string",
                    "description": "The MIME type to export Google Workspace files to (optional)",
                },
                "fileName": {
                    "type": "string",
                    "description": "Optional filename override",
                },
                "includeRevisions": {
                    "type": "boolean",
                    "description": "Whether to include revision history in the metadata (default: true, returns first 100 revisions)",
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
        }

        file_id = parameters["fileId"]
        mime_type = parameters.get("mimeType")
        file_name = parameters.get("fileName")
        include_revisions = parameters.get("includeRevisions", True)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields={self.ALL_FILE_FIELDS}&supportsAllDrives=true"
                metadata_resp = await client.get(metadata_url, headers=headers)

                if not 200 <= metadata_resp.status_code < 300:
                    try:
                        error_data = metadata_resp.json()
                        error_msg = error_data.get("error", {}).get("message", f"HTTP {metadata_resp.status_code}: Failed to get file metadata")
                    except:
                        error_msg = metadata_resp.text or "Failed to get file metadata"
                    return ToolResult(success=False, output="", error=error_msg)

                metadata = metadata_resp.json()
                file_mime_type = metadata["mimeType"]

                final_mime_type = file_mime_type
                file_bytes: bytes

                if file_mime_type in self.GOOGLE_WORKSPACE_MIME_TYPES:
                    export_format = mime_type or self.DEFAULT_EXPORT_FORMATS.get(file_mime_type, "text/plain")
                    final_mime_type = export_format
                    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType={quote(export_format)}&supportsAllDrives=true"
                    export_resp = await client.get(export_url, headers=headers)

                    if not 200 <= export_resp.status_code < 300:
                        try:
                            error_data = export_resp.json()
                            error_msg = error_data.get("error", {}).get("message", f"HTTP {export_resp.status_code}: Failed to export file")
                        except:
                            error_msg = export_resp.text or "Failed to export Google Workspace file"
                        return ToolResult(success=False, output="", error=error_msg)

                    file_bytes = await export_resp.aread()
                else:
                    download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
                    download_resp = await client.get(download_url, headers=headers)

                    if not 200 <= download_resp.status_code < 300:
                        try:
                            error_data = download_resp.json()
                            error_msg = error_data.get("error", {}).get("message", f"HTTP {download_resp.status_code}: Failed to download file")
                        except:
                            error_msg = download_resp.text or "Failed to download file"
                        return ToolResult(success=False, output="", error=error_msg)

                    file_bytes = await download_resp.aread()

                can_read_revisions = metadata.get("capabilities", {}).get("canReadRevisions", False)
                if include_revisions and can_read_revisions:
                    revisions_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/revisions?fields=revisions({self.ALL_REVISION_FIELDS})&pageSize=100"
                    revisions_resp = await client.get(revisions_url, headers=headers)

                    if 200 <= revisions_resp.status_code < 300:
                        revisions_data = revisions_resp.json()
                        metadata["revisions"] = revisions_data.get("revisions", [])

                resolved_name = file_name or metadata.get("name", "download")
                base64_data = base64.b64encode(file_bytes).decode("ascii")

                output_data = {
                    "file": {
                        "name": resolved_name,
                        "mimeType": final_mime_type,
                        "data": base64_data,
                        "size": len(file_bytes),
                    },
                    "metadata": metadata,
                }

                return ToolResult(
                    success=True,
                    output=f"Downloaded {resolved_name} ({len(file_bytes)} bytes)",
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
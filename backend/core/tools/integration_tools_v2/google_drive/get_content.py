from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDriveGetContentTool(BaseTool):
    name = "google_drive_get_content"
    description = "Get content from a file in Google Drive with complete metadata (exports Google Workspace files automatically)"
    category = "integration"

    GOOGLE_WORKSPACE_MIME_TYPES = [
        "application/vnd.google-apps.document",
        "application/vnd.google-apps.spreadsheet",
        "application/vnd.google-apps.presentation",
        "application/vnd.google-apps.drawing",
        "application/vnd.google-apps.form",
        "application/vnd.google-apps.script",
        "application/vnd.google-apps.map",
        "application/vnd.google-apps.page",
    ]

    DEFAULT_EXPORT_FORMATS = {
        "application/vnd.google-apps.document": "text/html",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/html",
        "application/vnd.google-apps.drawing": "image/png",
        "application/vnd.google-apps.form": "text/html",
        "application/vnd.google-apps.script": "application/vnd.google-apps.script+json",
        "application/vnd.google-apps.map": "application/json",
        "application/vnd.google-apps.page": "application/pdf",
    }

    ALL_FILE_FIELDS = (
        "id,kind,name,mimeType,description,originalFilename,fullFileExtension,fileExtension,"
        "owners,permissions,permissionIds,shared,ownedByMe,writersCanShare,viewersCanCopyContent,"
        "copyRequiresWriterPermission,sharingUser,starred,trashed,explicitlyTrashed,properties,"
        "appProperties,createdTime,modifiedTime,modifiedByMeTime,viewedByMeTime,sharedWithMeTime,"
        "lastModifyingUser,viewedByMe,modifiedByMe,webViewLink,webContentLink,iconLink,"
        "thumbnailLink,exportLinks,size,quotaBytesUsed,md5Checksum,sha1Checksum,sha256Checksum,"
        "parents,spaces,driveId,capabilities(canReadRevisions),version,headRevisionId,"
        "hasThumbnail,thumbnailVersion,imageMediaMetadata,videoMediaMetadata,"
        "isAppAuthorized,contentRestrictions,linkShareMetadata"
    )

    ALL_REVISION_FIELDS = (
        "id,kind,modifiedTime,lastModifyingUser,publishAuto,published,publishedOutsideDomain,"
        "size,md5Checksum"
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
            "google-drive",
            context=context,
            context_token_keys=("accessToken", "GOOGLE_DRIVE_ACCESS_TOKEN"),
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
                    "description": "The ID of the file to get content from",
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
        include_revisions = parameters.get("includeRevisions", True)
        export_mime_type = parameters.get("mimeType")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch metadata
                url_meta = f"https://www.googleapis.com/drive/v3/files/{file_id}"
                params_meta = {
                    "fields": self.ALL_FILE_FIELDS,
                    "supportsAllDrives": True,
                }
                resp_meta = await client.get(url_meta, headers=headers, params=params_meta)
                resp_meta.raise_for_status()
                metadata: Dict[str, Any] = resp_meta.json()

                mime_type = metadata["mimeType"]

                # Fetch content
                if mime_type in self.GOOGLE_WORKSPACE_MIME_TYPES:
                    export_format = export_mime_type or self.DEFAULT_EXPORT_FORMATS.get(mime_type) or "text/plain"
                    url_export = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
                    params_export = {
                        "mimeType": export_format,
                        "supportsAllDrives": True,
                    }
                    resp_content = await client.get(url_export, headers=headers, params=params_export)
                    resp_content.raise_for_status()
                    content = resp_content.text
                else:
                    url_download = f"https://www.googleapis.com/drive/v3/files/{file_id}"
                    params_download = {
                        "alt": "media",
                        "supportsAllDrives": True,
                    }
                    resp_content = await client.get(url_download, headers=headers, params=params_download)
                    resp_content.raise_for_status()
                    content = resp_content.text

                # Optionally fetch revisions
                if include_revisions and metadata.get("capabilities", {}).get("canReadRevisions", False):
                    url_revisions = f"https://www.googleapis.com/drive/v3/files/{file_id}/revisions"
                    params_revisions = {
                        "fields": f"revisions({self.ALL_REVISION_FIELDS})",
                        "pageSize": 100,
                    }
                    resp_revisions = await client.get(url_revisions, headers=headers, params=params_revisions)
                    if resp_revisions.status_code == 200:
                        revisions_data = resp_revisions.json()
                        metadata["revisions"] = revisions_data.get("revisions", [])
                    # else: continue without revisions

                result_data = {
                    "content": content,
                    "metadata": metadata,
                }

                return ToolResult(
                    success=True,
                    output=content,
                    data=result_data,
                )

        except httpx.HTTPStatusError as e:
            error_msg = e.response.text
            try:
                error_json = e.response.json()
                error_msg = error_json.get("error", {}).get("message", error_msg)
            except:
                pass
            return ToolResult(success=False, output="", error=f"API error ({e.response.status_code}): {error_msg}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
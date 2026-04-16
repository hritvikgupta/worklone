from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDriveListTool(BaseTool):
    name = "google_drive_list"
    description = "List files and folders in Google Drive with complete metadata"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _escape_query_value(self, value: str) -> str:
        return value.replace('\\', '\\\\').replace("'", "\\'")

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Access token",
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
                "folderSelector": {
                    "type": "string",
                    "description": "Google Drive folder ID to list files from (e.g., 1ABCxyz...)",
                },
                "query": {
                    "type": "string",
                    "description": 'Search term to filter files by name (e.g. "budget" finds files with "budget" in the name). Do NOT use Google Drive query syntax here - just provide a plain search term.',
                },
                "pageSize": {
                    "type": "number",
                    "description": "The maximum number of files to return (default: 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = "https://www.googleapis.com/drive/v3/files"
        params: Dict[str, str] = {
            "fields": "files(id,kind,name,mimeType,description,originalFilename,fullFileExtension,fileExtension,owners,permissions,permissionIds,shared,ownedByMe,writersCanShare,viewersCanCopyContent,copyRequiresWriterPermission,sharingUser,starred,trashed,explicitlyTrashed,properties,appProperties,createdTime,modifiedTime,modifiedByMeTime,viewedByMeTime,sharedWithMeTime,lastModifyingUser,viewedByMe,modifiedByMe,webViewLink,webContentLink,iconLink,thumbnailLink,exportLinks,size,quotaBytesUsed,md5Checksum,sha1Checksum,sha256Checksum,parents,spaces,driveId,capabilities,version,headRevisionId,hasThumbnail,thumbnailVersion,imageMediaMetadata,videoMediaMetadata,isAppAuthorized,contentRestrictions,linkShareMetadata),nextPageToken",
            "corpora": "allDrives",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        
        conditions = ["trashed = false"]
        folder_id = parameters.get("folderId") or parameters.get("folderSelector")
        if folder_id:
            escaped_folder_id = self._escape_query_value(folder_id)
            conditions.append(f"'{escaped_folder_id}' in parents")
        q = " and ".join(conditions)
        params["q"] = q
        
        query = parameters.get("query")
        if query:
            escaped_query = self._escape_query_value(query)
            query_part = f"name contains '{escaped_query}'"
            params["q"] += f" and {query_part}"
        
        page_size = parameters.get("pageSize")
        if page_size:
            params["pageSize"] = str(int(page_size))
        
        page_token = parameters.get("pageToken")
        if page_token:
            params["pageToken"] = page_token
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
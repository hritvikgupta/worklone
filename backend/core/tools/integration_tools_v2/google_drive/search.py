from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleDriveSearchTool(BaseTool):
    name = "google_drive_search"
    description = "Search for files in Google Drive using advanced query syntax (e.g., fullText contains, mimeType, modifiedTime, etc.)"
    category = "integration"

    FILE_FIELDS = [
        "id",
        "kind",
        "name",
        "mimeType",
        "description",
        "originalFilename",
        "fullFileExtension",
        "fileExtension",
        "owners",
        "permissions",
        "shared",
        "ownedByMe",
        "starred",
        "trashed",
        "createdTime",
        "modifiedTime",
        "lastModifyingUser",
        "webViewLink",
        "webContentLink",
        "iconLink",
        "thumbnailLink",
        "size",
        "parents",
        "driveId",
        "capabilities",
        "version",
    ]

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

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
            "google-drive",
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
                "query": {
                    "type": "string",
                    "description": "Google Drive query string using advanced search syntax (e.g., \"fullText contains 'budget'\", \"mimeType = 'application/pdf'\", \"modifiedTime > '2024-01-01'\")",
                },
                "pageSize": {
                    "type": "number",
                    "description": "Maximum number of files to return (default: 100)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Token for fetching the next page of results",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        fields_value = f"files({','.join(self.FILE_FIELDS)}),nextPageToken"
        query_params = {
            "fields": fields_value,
            "corpora": "allDrives",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        conditions = ["trashed = false"]
        query_str = parameters.get("query", "").strip()
        if query_str:
            conditions.append(query_str)
        query_params["q"] = " and ".join(conditions)
        if "pageSize" in parameters:
            query_params["pageSize"] = parameters["pageSize"]
        if "pageToken" in parameters:
            query_params["pageToken"] = parameters["pageToken"]
        
        url = "https://www.googleapis.com/drive/v3/files"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
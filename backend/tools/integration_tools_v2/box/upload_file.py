from typing import Any, Dict
import httpx
import base64
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxUploadFileTool(BaseTool):
    name = "box_upload_file"
    description = "Upload a file to a Box folder"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="BOX_ACCESS_TOKEN",
                description="OAuth access token for Box API",
                env_var="BOX_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "box",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("BOX_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "parentFolderId": {
                    "type": "string",
                    "description": "The ID of the folder to upload the file to (use \"0\" for root)",
                },
                "file": {
                    "type": "string",
                    "description": "The file to upload (UserFile object)",
                },
                "fileName": {
                    "type": "string",
                    "description": "Optional filename override",
                },
            },
            "required": ["parentFolderId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        parent_folder_id = parameters.get("parentFolderId")
        if not parent_folder_id:
            return ToolResult(success=False, output="", error="parentFolderId is required.")
        
        content_b64 = parameters.get("file") or parameters.get("fileContent")
        if not content_b64:
            return ToolResult(success=False, output="", error="file or fileContent is required.")
        
        file_name = parameters.get("fileName", "uploaded_file")
        
        try:
            file_bytes = base64.b64decode(content_b64)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Invalid base64 file content: {str(e)}")
        
        attributes = {
            "name": file_name,
            "parent": {"id": parent_folder_id},
        }
        attributes_str = json.dumps(attributes)
        
        files = {
            "attributes": (None, attributes_str, "application/json"),
            "contents": (file_name, file_bytes, "application/octet-stream"),
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = "https://upload.box.com/api/2.0/files/content"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, files=files)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict, Optional
import httpx
import mimetypes
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseUploadFileTool(BaseTool):
    name = "microsoft_dataverse_upload_file"
    description = "Upload a file to a file or image column on a Dataverse record. Supports single-request upload for files up to 128 MB. The file content must be provided as a base64-encoded string."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_DATAVERSE_ACCESS_TOKEN",
                description="OAuth access token for Microsoft Dataverse API",
                env_var="MICROSOFT_DATAVERSE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "microsoft-dataverse",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("MICROSOFT_DATAVERSE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _get_file_content(self, parameters: dict) -> Optional[str]:
        content = parameters.get("fileContent")
        if content:
            return content.strip()
        file_data = parameters.get("file")
        if file_data:
            if isinstance(file_data, str):
                return file_data.strip()
            if isinstance(file_data, dict):
                return (file_data.get("content") or file_data.get("base64") or file_data.get("data", "")).strip()
        return None

    def _infer_mimetype(self, filename: str) -> str:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "environmentUrl": {
                    "type": "string",
                    "description": "Dataverse environment URL (e.g., https://myorg.crm.dynamics.com)",
                },
                "entitySetName": {
                    "type": "string",
                    "description": "Entity set name (plural table name, e.g., accounts, contacts)",
                },
                "recordId": {
                    "type": "string",
                    "description": "Record GUID to upload the file to",
                },
                "fileColumn": {
                    "type": "string",
                    "description": "File or image column logical name (e.g., entityimage, cr_document)",
                },
                "fileName": {
                    "type": "string",
                    "description": "Name of the file being uploaded (e.g., document.pdf)",
                },
                "fileContent": {
                    "type": "string",
                    "description": "Base64-encoded file content",
                },
            },
            "required": ["environmentUrl", "entitySetName", "recordId", "fileColumn", "fileName", "fileContent"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        required_params = ["environmentUrl", "entitySetName", "recordId", "fileColumn", "fileName"]
        for param in required_params:
            if param not in parameters or not parameters[param]:
                return ToolResult(success=False, output="", error=f"Missing required parameter: {param}")
        
        file_content = self._get_file_content(parameters)
        if not file_content:
            return ToolResult(
                success=False,
                output="",
                error="File content is required. Provide 'fileContent' as base64 string or 'file' with content.",
            )
        
        environment_url = parameters["environmentUrl"].rstrip("/")
        entity_set_name = parameters["entitySetName"]
        record_id = parameters["recordId"]
        file_column = parameters["fileColumn"]
        file_name = parameters["fileName"]
        
        url = f"{environment_url}/api/data/v9.2/{entity_set_name}({record_id})"
        
        body = {
            file_column: f"/{file_content}",
            f"{file_column}filename": file_name,
            f"{file_column}mimetype": self._infer_mimetype(file_name),
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 204]:
                    data = response.json() if response.status_code == 200 else {}
                    return ToolResult(
                        success=True,
                        output="File uploaded successfully.",
                        data={
                            "recordId": record_id,
                            "fileColumn": file_column,
                            "fileName": file_name,
                            **data,
                        },
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
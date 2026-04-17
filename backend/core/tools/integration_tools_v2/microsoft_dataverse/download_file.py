from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftDataverseDownloadFileTool(BaseTool):
    name = "microsoft_dataverse_download_file"
    description = "Download a file from a file or image column on a Dataverse record. Returns the file content as a base64-encoded string along with file metadata from response headers."
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
                    "description": "Record GUID to download the file from",
                },
                "fileColumn": {
                    "type": "string",
                    "description": "File or image column logical name (e.g., entityimage, cr_document)",
                },
            },
            "required": ["environmentUrl", "entitySetName", "recordId", "fileColumn"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        
        base_url = parameters["environmentUrl"].rstrip("/")
        url = f"{base_url}/api/data/v9.2/{parameters['entitySetName']}({parameters['recordId']})/{parameters['fileColumn']}/$value"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    file_name = response.headers.get("x-ms-file-name", "")
                    file_size_str = response.headers.get("x-ms-file-size", "")
                    mime_type = response.headers.get("mimetype") or response.headers.get("content-type", "")
                    content = response.content
                    base64_content = base64.b64encode(content).decode("utf-8")
                    file_size = int(file_size_str) if file_size_str else len(content)
                    data = {
                        "fileContent": base64_content,
                        "fileName": file_name,
                        "fileSize": file_size,
                        "mimeType": mime_type,
                        "success": True,
                    }
                    return ToolResult(success=True, output=json.dumps(data), data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", f"Dataverse API error: {response.status_code} {response.reason_phrase}")
                    except:
                        error_msg = response.text or f"Dataverse API error: {response.status_code}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
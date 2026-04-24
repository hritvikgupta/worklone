import httpx
import base64
import re
from urllib.parse import quote
from typing import Dict, Any, List
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class MicrosoftTeamsFileUploadTool(BaseTool):
    name = "microsoft_teams_upload_files"
    description = "Processes and uploads files to OneDrive TeamsAttachments folder, returning attachment references for Teams messages and processed file outputs. Max 4MB per file."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="MICROSOFT_ACCESS_TOKEN",
                description="Microsoft Graph access token",
                env_var="MICROSOFT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection("microsoft_teams",
            context=context,
            context_token_keys=("microsoft_token",),
            env_token_keys=("MICROSOFT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "description": "List of files to upload as attachments for Teams messages",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The name of the file"
                            },
                            "mimeType": {
                                "type": "string",
                                "description": "The MIME type of the file (optional, defaults to application/octet-stream)"
                            },
                            "data": {
                                "type": "string",
                                "description": "Base64-encoded content of the file"
                            }
                        },
                        "required": ["name", "data"]
                    }
                }
            },
            "required": ["files"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        files = parameters.get("files", [])
        attachments: List[Dict[str, Any]] = []
        files_output: List[Dict[str, Any]] = []
        MAX_TEAMS_FILE_SIZE = 4 * 1024 * 1024
        
        try:
            if files:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    for file_info in files:
                        name = file_info["name"]
                        mime_type = file_info.get("mimeType", "application/octet-stream")
                        data_b64 = file_info["data"]
                        buffer = base64.b64decode(data_b64)
                        size = len(buffer)
                        if size > MAX_TEAMS_FILE_SIZE:
                            size_mb = size / (1024 * 1024)
                            raise ValueError(
                                f'File "{name}" ({size_mb:.2f}MB) exceeds the 4MB limit for Teams attachments. Use smaller files or upload to SharePoint/OneDrive first.'
                            )
                        files_output.append({
                            "name": name,
                            "mimeType": mime_type,
                            "data": data_b64,
                            "size": size,
                        })
                        upload_url = (
                            "https://graph.microsoft.com/v1.0/me/drive/root:/TeamsAttachments/"
                            + quote(name)
                            + ":/content"
                        )
                        upload_headers = {
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": mime_type,
                        }
                        response = await client.put(upload_url, headers=upload_headers, content=buffer)
                        
                        if not (200 <= response.status_code < 300):
                            try:
                                error_data = response.json()
                            except Exception:
                                error_data = {}
                            error_msg = error_data.get("error", {}).get("message", response.text or "Unknown error")
                            raise ValueError(f"Failed to upload file to Teams: {error_msg}")
                        
                        uploaded_file = response.json()
                        file_id = uploaded_file["id"]
                        details_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}?select=id,name,webDavUrl,eTag,size"
                        details_headers = {
                            "Authorization": f"Bearer {access_token}",
                        }
                        details_response = await client.get(details_url, headers=details_headers)
                        
                        if details_response.status_code != 200:
                            try:
                                error_data = details_response.json()
                            except Exception:
                                error_data = {}
                            error_msg = error_data.get("error", {}).get("message", details_response.text or "Unknown error")
                            raise ValueError(f"Failed to get file details: {error_msg}")
                        
                        file_details = details_response.json()
                        web_dav_url = file_details.get("webDavUrl")
                        if not web_dav_url:
                            raise ValueError(
                                f'Failed to get file URL for attachment "{name}". The file was uploaded but Teams attachment reference could not be created.'
                            )
                        
                        e_tag = file_details.get("eTag", "")
                        e_tag_match = re.search(r"\{([a-f0-9-]+)\}", e_tag, re.IGNORECASE)
                        attachment_id = e_tag_match.group(1) if e_tag_match else file_id
                        attachments.append({
                            "id": attachment_id,
                            "contentType": "reference",
                            "contentUrl": web_dav_url,
                            "name": name,
                        })
            
            return ToolResult(
                success=True,
                output="All files uploaded successfully and attachment references created.",
                data={"attachments": attachments, "filesOutput": files_output}
            )
            
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DropboxUploadTool(BaseTool):
    name = "dropbox_upload"
    description = "Upload a file to Dropbox"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DROPBOX_ACCESS_TOKEN",
                description="Dropbox access token",
                env_var="DROPBOX_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "dropbox",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("DROPBOX_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path in Dropbox where the file should be saved (e.g., /folder/document.pdf)",
                },
                "file": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the file",
                        },
                        "content": {
                            "type": "string",
                            "description": "Base64 encoded file content",
                        },
                    },
                    "description": "The file to upload (UserFile object)",
                },
                "fileContent": {
                    "type": "string",
                    "description": "Legacy: base64 encoded file content",
                },
                "fileName": {
                    "type": "string",
                    "description": "Optional filename (used if path is a folder)",
                },
                "mode": {
                    "type": "string",
                    "enum": ["add", "overwrite"],
                    "description": "Write mode: add (default) or overwrite",
                },
                "autorename": {
                    "type": "boolean",
                    "description": "If true, rename the file if there is a conflict",
                },
                "mute": {
                    "type": "boolean",
                    "description": "If true, don't notify the user about this upload",
                },
            },
            "required": ["path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        file_param = parameters.get("file")
        file_content_legacy = parameters.get("fileContent")
        
        file_buffer: bytes | None = None
        file_name: str = "file"
        
        if file_param:
            if isinstance(file_param, dict):
                file_name = file_param.get("name", parameters.get("fileName", "file"))
                content_b64 = file_param.get("content") or file_param.get("data")
                if not content_b64:
                    return ToolResult(success=False, output="", error="File content missing")
                try:
                    file_buffer = base64.b64decode(content_b64)
                except Exception as e:
                    return ToolResult(success=False, output="", error=f"Invalid base64 content: {str(e)}")
            else:
                file_name = parameters.get("fileName", "file")
                try:
                    file_buffer = base64.b64decode(str(file_param))
                except Exception as e:
                    return ToolResult(success=False, output="", error=f"Invalid base64 file: {str(e)}")
        elif file_content_legacy:
            file_name = parameters.get("fileName", "file")
            try:
                file_buffer = base64.b64decode(file_content_legacy)
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Invalid base64 fileContent: {str(e)}")
        else:
            return ToolResult(success=False, output="", error="File or fileContent is required")
        
        if not file_buffer:
            return ToolResult(success=False, output="", error="No file content provided")
        
        path = parameters.get("path")
        if not isinstance(path, str) or not path.strip():
            return ToolResult(success=False, output="", error="Valid path is required")
        
        final_path = path
        if path.endswith("/"):
            final_path += file_name
        
        mode = parameters.get("mode", "add")
        autorename = parameters.get("autorename", True)
        mute = parameters.get("mute", False)
        
        dropbox_api_arg = {
            "path": final_path,
            "mode": mode,
            "autorename": autorename,
            "mute": mute,
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": json.dumps(dropbox_api_arg),
        }
        
        url = "https://content.dropboxapi.com/2/files/upload"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, content=file_buffer)
            
            if response.status_code == 200:
                data = response.json()
                return ToolResult(success=True, output=response.text, data={"file": data})
            else:
                try:
                    data = response.json()
                    error_message = (
                        data.get("error_summary")
                        or data.get("error", {}).get("message")
                        or response.text
                    )
                except Exception:
                    error_message = response.text
                return ToolResult(success=False, output="", error=error_message)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
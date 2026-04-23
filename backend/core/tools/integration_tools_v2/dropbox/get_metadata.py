from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DropboxGetMetadataTool(BaseTool):
    name = "dropbox_get_metadata"
    description = "Get metadata for a file or folder in Dropbox"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DROPBOX_ACCESS_TOKEN",
                description="Access token",
                env_var="DROPBOX_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "dropbox",
            context=context,
            context_token_keys=("dropbox_token",),
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
                    "description": "The path of the file or folder to get metadata for",
                },
                "includeMediaInfo": {
                    "type": "boolean",
                    "description": "If true, include media info for photos/videos",
                },
                "includeDeleted": {
                    "type": "boolean",
                    "description": "If true, include deleted files in results",
                },
            },
            "required": ["path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.dropboxapi.com/2/files/get_metadata"
        
        json_body = {
            "path": parameters["path"],
            "include_media_info": parameters.get("includeMediaInfo", False),
            "include_deleted": parameters.get("includeDeleted", False),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
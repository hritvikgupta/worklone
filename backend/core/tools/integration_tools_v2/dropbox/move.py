from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DropboxMoveTool(BaseTool):
    name = "dropbox_move"
    description = "Move or rename a file or folder in Dropbox"
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
                "fromPath": {
                    "type": "string",
                    "description": "The source path of the file or folder to move",
                },
                "toPath": {
                    "type": "string",
                    "description": "The destination path for the moved file or folder",
                },
                "autorename": {
                    "type": "boolean",
                    "description": "If true, rename the file if there is a conflict at destination",
                },
            },
            "required": ["fromPath", "toPath"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.dropboxapi.com/2/files/move_v2"
        
        json_body = {
            "from_path": parameters["fromPath"],
            "to_path": parameters["toPath"],
            "autorename": parameters.get("autorename", False),
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
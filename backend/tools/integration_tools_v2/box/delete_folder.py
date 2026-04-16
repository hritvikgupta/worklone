from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxDeleteFolderTool(BaseTool):
    name = "box_delete_folder"
    description = "Delete a folder from Box"
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
            context_token_keys=("access_token",),
            env_token_keys=("BOX_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "folderId": {
                    "type": "string",
                    "description": "The ID of the folder to delete",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Delete folder and all its contents recursively",
                },
            },
            "required": ["folderId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        folder_id = parameters["folderId"].strip()
        url = f"https://api.box.com/2.0/folders/{folder_id}"
        if parameters.get("recursive"):
            url += "?recursive=true"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code == 204:
                    result_data = {
                        "deleted": True,
                        "message": "Folder deleted successfully",
                    }
                    return ToolResult(success=True, output=str(result_data), data=result_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
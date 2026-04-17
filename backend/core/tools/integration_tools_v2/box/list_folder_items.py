from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxListFolderItemsTool(BaseTool):
    name = "box_list_folder_items"
    description = "List files and folders in a Box folder"
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
                "folderId": {
                    "type": "string",
                    "description": "The ID of the folder to list items from (use \"0\" for root)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of items to return per page",
                },
                "offset": {
                    "type": "number",
                    "description": "The offset for pagination",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort field: id, name, date, or size",
                },
                "direction": {
                    "type": "string",
                    "description": "Sort direction: ASC or DESC",
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
        url = f"https://api.box.com/2.0/folders/{folder_id}/items"
        
        query_params = {}
        for param_name in ["limit", "offset", "sort", "direction"]:
            value = parameters.get(param_name)
            if value is not None:
                query_params[param_name] = value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
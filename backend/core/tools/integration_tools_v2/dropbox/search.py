from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class DropboxSearchTool(BaseTool):
    name = "dropbox_search"
    description = "Search for files and folders in Dropbox"
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
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "path": {
                    "type": "string",
                    "description": "Dropbox folder path to limit search scope (e.g., /folder/subfolder)",
                },
                "fileExtensions": {
                    "type": "string",
                    "description": "Comma-separated list of file extensions to filter by (e.g., pdf,xlsx)",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results to return (default: 100)",
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
            "Content-Type": "application/json",
        }
        
        url = "https://api.dropboxapi.com/2/files/search_v2"
        
        body = {
            "query": parameters["query"],
        }
        options = {}
        path = parameters.get("path")
        if path:
            options["path"] = path
        file_extensions_str = parameters.get("fileExtensions")
        if file_extensions_str:
            extensions = [
                ext.strip() for ext in file_extensions_str.split(",") if ext.strip()
            ]
            if extensions:
                options["file_extensions"] = extensions
        max_results = parameters.get("maxResults")
        if max_results:
            options["max_results"] = max_results
        if options:
            body["options"] = options
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
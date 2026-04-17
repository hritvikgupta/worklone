from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class BoxSearchTool(BaseTool):
    name = "box_search"
    description = "Search for files and folders in Box"
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
                "query": {
                    "type": "string",
                    "description": "The search query string",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return",
                },
                "offset": {
                    "type": "number",
                    "description": "The offset for pagination",
                },
                "ancestorFolderId": {
                    "type": "string",
                    "description": "Restrict search to a specific folder and its subfolders",
                },
                "fileExtensions": {
                    "type": "string",
                    "description": "Comma-separated file extensions to filter by (e.g., pdf,docx)",
                },
                "type": {
                    "type": "string",
                    "description": "Restrict to a specific content type: file, folder, or web_link",
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
        }

        url = "https://api.box.com/2.0/search"

        params_dict: Dict[str, Any] = {
            "query": parameters["query"],
        }
        if "limit" in parameters:
            params_dict["limit"] = parameters["limit"]
        if "offset" in parameters:
            params_dict["offset"] = parameters["offset"]
        if "ancestorFolderId" in parameters and parameters["ancestorFolderId"]:
            params_dict["ancestor_folder_ids"] = str(parameters["ancestorFolderId"]).strip()
        if "fileExtensions" in parameters and parameters["fileExtensions"]:
            params_dict["file_extensions"] = parameters["fileExtensions"]
        if "type" in parameters and parameters["type"]:
            params_dict["type"] = parameters["type"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
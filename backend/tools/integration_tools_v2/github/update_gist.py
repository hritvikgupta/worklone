from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubUpdateGistTool(BaseTool):
    name = "github_update_gist"
    description = "Update a gist description or files. To delete a file, set its value to null in files object"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub API token",
                env_var="GITHUB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("provider_token", "apiKey", "github_token"),
            env_token_keys=("GITHUB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "gist_id": {
                    "type": "string",
                    "description": "The gist ID to update",
                },
                "description": {
                    "type": "string",
                    "description": "New description for the gist",
                },
                "files": {
                    "type": "string",
                    "description": "JSON object with filenames as keys. Set to null to delete, or provide content to update/add",
                },
            },
            "required": ["gist_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        gist_id = parameters["gist_id"].strip()
        url = f"https://api.github.com/gists/{gist_id}"
        
        body: Dict[str, Any] = {}
        description = parameters.get("description")
        if "description" in parameters:
            body["description"] = description
        files_str = parameters.get("files")
        if files_str:
            body["files"] = json.loads(files_str)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
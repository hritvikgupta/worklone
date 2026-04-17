from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubUpdateFileTool(BaseTool):
    name = "github_update_file"
    description = "Update an existing file in a GitHub repository. Requires the file SHA. Content will be automatically Base64 encoded. Supports files up to 1MB."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub Personal Access Token",
                env_var="GITHUB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("GITHUB_ACCESS_TOKEN",),
            env_token_keys=("GITHUB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner (user or organization)",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "path": {
                    "type": "string",
                    "description": 'Path to the file to update (e.g., "src/index.ts")',
                },
                "message": {
                    "type": "string",
                    "description": "Commit message for this file update",
                },
                "content": {
                    "type": "string",
                    "description": "New file content (plain text, will be Base64 encoded automatically)",
                },
                "sha": {
                    "type": "string",
                    "description": "The blob SHA of the file being replaced (get from github_get_file_content)",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to update the file in (defaults to repository default branch)",
                },
            },
            "required": ["owner", "repo", "path", "message", "content", "sha"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        path = parameters["path"]
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        
        body = {
            "message": parameters["message"],
            "content": base64.b64encode(parameters["content"].encode("utf-8")).decode("utf-8"),
            "sha": parameters["sha"],
        }
        branch = parameters.get("branch")
        if branch:
            body["branch"] = branch
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
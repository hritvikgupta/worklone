from typing import Any, Dict
import httpx
import os
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class GitHubDeleteFileTool(BaseTool):
    name = "github_delete_file"
    description = "Delete a file from a GitHub repository. Requires the file SHA. This operation cannot be undone through the API."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="GitHub Personal Access Token",
                env_var="GITHUB_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("apiKey") if context else None
        if api_key is None:
            api_key = os.getenv("GITHUB_API_KEY")
        return api_key or ""

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
                    "description": 'Path to the file to delete (e.g., "src/oldfile.ts")',
                },
                "message": {
                    "type": "string",
                    "description": "Commit message for this file deletion",
                },
                "sha": {
                    "type": "string",
                    "description": "The blob SHA of the file being deleted (get from github_get_file_content)",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to delete the file from (defaults to repository default branch)",
                },
            },
            "required": ["owner", "repo", "path", "message", "sha"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="GitHub API key not configured.")

        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {api_key}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/contents/{parameters['path']}"

        body = {
            "message": parameters["message"],
            "sha": parameters["sha"],
        }
        if "branch" in parameters and parameters["branch"]:
            body["branch"] = parameters["branch"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubCompareCommitsTool(BaseTool):
    name = "github_compare_commits"
    description = "Compare two commits or branches to see the diff, commits between them, and changed files"
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
            context_token_keys=("github_token",),
            env_token_keys=("GITHUB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "owner": {
                    "type": "string",
                    "description": "Repository owner",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "base": {
                    "type": "string",
                    "description": "Base branch/tag/SHA for comparison",
                },
                "head": {
                    "type": "string",
                    "description": "Head branch/tag/SHA for comparison",
                },
                "per_page": {
                    "type": "number",
                    "description": "Results per page for files (max 100, default: 30)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for files (default: 1)",
                },
            },
            "required": ["owner", "repo", "base", "head"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        base = parameters["base"]
        head = parameters["head"]
        url = f"https://api.github.com/repos/{owner}/{repo}/compare/{base}...{head}"
        
        params: Dict[str, Any] = {}
        if "per_page" in parameters:
            params["per_page"] = parameters["per_page"]
        if "page" in parameters:
            params["page"] = parameters["page"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    processed_data = {
                        **data,
                        "commits": data.get("commits", []),
                        "files": data.get("files", []),
                    }
                    return ToolResult(success=True, output=response.text, data=processed_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
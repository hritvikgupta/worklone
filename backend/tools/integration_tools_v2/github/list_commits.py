from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubListCommitsTool(BaseTool):
    name = "github_list_commits"
    description = "List commits in a repository with optional filtering by SHA, path, author, committer, or date range"
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
                    "description": "Repository owner",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "sha": {
                    "type": "string",
                    "description": "SHA or branch to start listing commits from",
                },
                "path": {
                    "type": "string",
                    "description": "Only commits containing this file path",
                },
                "author": {
                    "type": "string",
                    "description": "GitHub login or email address to filter by author",
                },
                "committer": {
                    "type": "string",
                    "description": "GitHub login or email address to filter by committer",
                },
                "since": {
                    "type": "string",
                    "description": "Only commits after this date (ISO 8601 format)",
                },
                "until": {
                    "type": "string",
                    "description": "Only commits before this date (ISO 8601 format)",
                },
                "per_page": {
                    "type": "number",
                    "description": "Results per page (max 100, default: 30)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number (default: 1)",
                },
            },
            "required": ["owner", "repo"],
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
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        
        query_params = {}
        for key in ["sha", "path", "author", "committer", "since", "until", "per_page", "page"]:
            if key in parameters and parameters[key] is not None:
                query_params[key] = parameters[key]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    data = response.json()
                    items = [
                        {**item, "author": item.get("author"), "committer": item.get("committer")}
                        for item in data
                    ]
                    transformed = {
                        "items": items,
                        "count": len(items),
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
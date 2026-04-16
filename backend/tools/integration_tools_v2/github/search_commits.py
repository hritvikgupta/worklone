from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubSearchCommitsTool(BaseTool):
    name = "github_search_commits"
    description = "Search for commits across GitHub. Use qualifiers like repo:owner/name, author:user, committer:user, author-date:>2023-01-01"
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
            context_token_keys=("apiKey",),
            env_token_keys=("GITHUB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Search query with optional qualifiers (repo:, author:, committer:, author-date:, committer-date:, merge:true/false)",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by: author-date or committer-date (default: best match)",
                    "enum": ["author-date", "committer-date"],
                },
                "order": {
                    "type": "string",
                    "description": "Sort order: asc or desc (default: desc)",
                    "enum": ["asc", "desc"],
                },
                "per_page": {
                    "type": "number",
                    "description": "Results per page (max 100, default: 30)",
                    "default": 30,
                    "maximum": 100,
                },
                "page": {
                    "type": "number",
                    "description": "Page number (default: 1)",
                    "default": 1,
                },
            },
            "required": ["q"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github.cloak-preview+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        url = "https://api.github.com/search/commits"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=parameters)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
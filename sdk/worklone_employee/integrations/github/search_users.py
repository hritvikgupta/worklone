from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GithubSearchUsersTool(BaseTool):
    name = "github_search_users"
    description = "Search for users and organizations on GitHub. Use qualifiers like type:user, type:org, followers:>1000, repos:>10, location:city"
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
                "q": {
                    "type": "string",
                    "description": "Search query with optional qualifiers (type:user/org, followers:, repos:, location:, language:, created:)",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by: followers, repositories, joined (default: best match)",
                    "enum": ["followers", "repositories", "joined"],
                },
                "order": {
                    "type": "string",
                    "description": "Sort order: asc or desc (default: desc)",
                    "enum": ["asc", "desc"],
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
            "required": ["q"],
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
        
        url = "https://api.github.com/search/users"
        query_params = {"q": parameters["q"]}
        for key in ["sort", "order", "per_page", "page"]:
            if key in parameters:
                query_params[key] = parameters[key]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
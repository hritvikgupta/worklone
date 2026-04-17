from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubSearchReposTool(BaseTool):
    name = "github_search_repos"
    description = "Search for repositories across GitHub. Use qualifiers like language:python, stars:>1000, topic:react, user:owner, org:name"
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
                    "description": "Search query with optional qualifiers (language:, stars:, forks:, topic:, user:, org:, in:name,description,readme)",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by: stars, forks, help-wanted-issues, updated (default: best match)",
                },
                "order": {
                    "type": "string",
                    "description": "Sort order: asc or desc (default: desc)",
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
        
        url = "https://api.github.com/search/repositories"
        query_params = {"q": parameters["q"]}
        for param_name in ["sort", "order", "per_page", "page"]:
            value = parameters.get(param_name)
            if value is not None:
                query_params[param_name] = value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", []):
                        item["description"] = item.get("description")
                        item["language"] = item.get("language")
                        item["topics"] = item.get("topics", [])
                        item["license"] = item.get("license")
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
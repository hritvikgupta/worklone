from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubListForksTool(BaseTool):
    name = "github_list_forks"
    description = "List forks of a repository"
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
                "sort": {
                    "type": "string",
                    "description": "Sort by: newest, oldest, stargazers, watchers (default: newest)",
                    "default": "newest",
                    "enum": ["newest", "oldest", "stargazers", "watchers"],
                },
                "per_page": {
                    "type": "number",
                    "description": "Results per page (max 100, default: 30)",
                    "default": 30,
                },
                "page": {
                    "type": "number",
                    "description": "Page number (default: 1)",
                    "default": 1,
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
        url = f"https://api.github.com/repos/{owner}/{repo}/forks"
        
        query_params: Dict[str, Any] = {}
        sort = parameters.get("sort")
        if sort is not None:
            query_params["sort"] = sort
        per_page = parameters.get("per_page")
        if per_page is not None:
            query_params["per_page"] = per_page
        page = parameters.get("page")
        if page is not None:
            query_params["page"] = page
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200]:
                    data_list = response.json()
                    output_data = {
                        "items": data_list,
                        "count": len(data_list),
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
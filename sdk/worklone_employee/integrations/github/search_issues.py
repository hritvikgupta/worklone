from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class GitHubSearchIssuesTool(BaseTool):
    name = "github_search_issues"
    description = "Search for issues and pull requests across GitHub. Use qualifiers like repo:owner/name, is:issue, is:pr, state:open, label:bug, author:user"
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
        if context is None:
            return ""
        return context.get("GITHUB_ACCESS_TOKEN") or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "Search query with optional qualifiers (repo:, is:issue, is:pr, state:, label:, author:, assignee:)",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by: comments, reactions, created, updated, interactions (default: best match)",
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
        
        url = "https://api.github.com/search/issues"
        params_dict = {
            "q": parameters["q"],
        }
        for key in ("sort", "order", "per_page", "page"):
            if key in parameters:
                params_dict[key] = parameters[key]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
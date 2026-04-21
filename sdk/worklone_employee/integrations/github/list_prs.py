from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubListPRsTool(BaseTool):
    name = "github_list_prs"
    description = "List pull requests in a GitHub repository"
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
            context_token_keys=("provider_token",),
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
                "state": {
                    "type": "string",
                    "description": "Filter by state: open, closed, or all",
                    "default": "open",
                },
                "head": {
                    "type": "string",
                    "description": "Filter by head user or branch name (format: user:ref-name or organization:ref-name)",
                },
                "base": {
                    "type": "string",
                    "description": "Filter by base branch name",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by: created, updated, popularity, or long-running",
                    "default": "created",
                },
                "direction": {
                    "type": "string",
                    "description": "Sort direction: asc or desc",
                    "default": "desc",
                },
                "per_page": {
                    "type": "number",
                    "description": "Results per page (max 100)",
                    "default": 30,
                },
                "page": {
                    "type": "number",
                    "description": "Page number",
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
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        
        params_with_defaults = {
            "state": parameters.get("state", "open"),
            "head": parameters.get("head"),
            "base": parameters.get("base"),
            "sort": parameters.get("sort", "created"),
            "direction": parameters.get("direction", "desc"),
            "per_page": parameters.get("per_page", 30),
            "page": parameters.get("page", 1),
        }
        
        query_params: dict[str, str | int] = {}
        for key, value in params_with_defaults.items():
            if value:
                if key in ("per_page", "page"):
                    query_params[key] = int(value)
                else:
                    query_params[key] = value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    prs = response.json()
                    output_data = {
                        "items": prs or [],
                        "count": len(prs) if prs is not None else 0,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
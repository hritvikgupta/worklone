from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubListIssuesTool(BaseTool):
    name = "github_list_issues"
    description = "List issues in a GitHub repository. Note: This includes pull requests as PRs are considered issues in GitHub"
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
                    "description": "Filter by state: open, closed, or all (default: open)",
                },
                "assignee": {
                    "type": "string",
                    "description": "Filter by assignee username",
                },
                "creator": {
                    "type": "string",
                    "description": "Filter by creator username",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names to filter by",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by: created, updated, or comments (default: created)",
                },
                "direction": {
                    "type": "string",
                    "description": "Sort direction: asc or desc (default: desc)",
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
        
        url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/issues"
        
        query_params: Dict[str, Any] = {}
        for key in ["state", "assignee", "creator", "labels", "sort", "direction", "per_page", "page"]:
            value = parameters.get(key)
            if value is not None:
                query_params[key] = int(value) if isinstance(value, (int, float)) else value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    issues = response.json()
                    items = []
                    for issue in issues:
                        item = {**issue}
                        item["body"] = issue.get("body")
                        item["milestone"] = issue.get("milestone")
                        item["closed_at"] = issue.get("closed_at")
                        item["labels"] = issue.get("labels", [])
                        item["assignees"] = issue.get("assignees", [])
                        items.append(item)
                    output_data = {
                        "items": items,
                        "count": len(issues),
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
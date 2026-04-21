from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubListPRCommentsTool(BaseTool):
    name = "github_list_pr_comments"
    description = "List all review comments on a GitHub pull request"
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
                "pullNumber": {
                    "type": "integer",
                    "description": "Pull request number",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by created or updated",
                },
                "direction": {
                    "type": "string",
                    "description": "Sort direction (asc or desc)",
                },
                "since": {
                    "type": "string",
                    "description": "Only show comments updated after this ISO 8601 timestamp",
                },
                "per_page": {
                    "type": "integer",
                    "description": "Number of results per page (max 100)",
                },
                "page": {
                    "type": "integer",
                    "description": "Page number",
                },
            },
            "required": ["owner", "repo", "pullNumber"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        pull_number = int(parameters["pullNumber"])
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/comments"
        
        params_dict: Dict[str, Any] = {}
        sort = parameters.get("sort")
        if sort:
            params_dict["sort"] = sort
        direction = parameters.get("direction")
        if direction:
            params_dict["direction"] = direction
        since = parameters.get("since")
        if since:
            params_dict["since"] = since
        per_page = parameters.get("per_page")
        if per_page is not None:
            params_dict["per_page"] = int(per_page)
        page = parameters.get("page")
        if page is not None:
            params_dict["page"] = int(page)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
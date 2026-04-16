from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitLabListIssuesTool(BaseTool):
    name = "gitlab_list_issues"
    description = "List issues in a GitLab project"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITLAB_ACCESS_TOKEN",
                description="GitLab Personal Access Token",
                env_var="GITLAB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "gitlab",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GITLAB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or URL-encoded path",
                },
                "state": {
                    "type": "string",
                    "description": "Filter by state (opened, closed, all)",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names",
                },
                "assigneeId": {
                    "type": "number",
                    "description": "Filter by assignee user ID",
                },
                "milestoneTitle": {
                    "type": "string",
                    "description": "Filter by milestone title",
                },
                "search": {
                    "type": "string",
                    "description": "Search issues by title and description",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order by field (created_at, updated_at)",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort direction (asc, desc)",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page (default 20, max 100)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination",
                },
            },
            "required": ["projectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "PRIVATE-TOKEN": access_token,
        }
        
        project_id = parameters["projectId"]
        encoded_id = quote(str(project_id))
        url = f"https://gitlab.com/api/v4/projects/{encoded_id}/issues"
        
        params_dict = {
            "state": parameters.get("state"),
            "labels": parameters.get("labels"),
            "assignee_id": parameters.get("assigneeId"),
            "milestone": parameters.get("milestoneTitle"),
            "search": parameters.get("search"),
            "order_by": parameters.get("orderBy"),
            "sort": parameters.get("sort"),
            "per_page": parameters.get("perPage"),
            "page": parameters.get("page"),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code == 200:
                    issues = response.json()
                    total_header = response.headers.get("x-total")
                    total = int(total_header) if total_header else len(issues)
                    data = {
                        "issues": issues,
                        "total": total,
                    }
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=f"GitLab API error: {response.status_code} {response.text}")
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
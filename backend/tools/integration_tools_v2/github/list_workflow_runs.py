from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubListWorkflowRunsTool(BaseTool):
    name = "github_list_workflow_runs"
    description = "List workflow runs for a repository. Supports filtering by actor, branch, event, and status. Returns run details including status, conclusion, and links."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub Personal Access Token",
                env_var="GITHUB_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
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
                    "description": "Repository owner (user or organization)",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "actor": {
                    "type": "string",
                    "description": "Filter by user who triggered the workflow",
                },
                "branch": {
                    "type": "string",
                    "description": "Filter by branch name",
                },
                "event": {
                    "type": "string",
                    "description": "Filter by event type (e.g., push, pull_request, workflow_dispatch)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (queued, in_progress, completed, waiting, requested, pending)",
                },
                "per_page": {
                    "type": "number",
                    "description": "Number of results per page (default: 30, max: 100)",
                    "default": 30,
                },
                "page": {
                    "type": "number",
                    "description": "Page number of results to fetch (default: 1)",
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
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/actions/runs"
        
        query_params: Dict[str, str] = {}
        for param_name in ("actor", "branch", "event", "status"):
            param_value = parameters.get(param_name)
            if param_value:
                query_params[param_name] = str(param_value)
        per_page = parameters.get("per_page")
        if per_page is not None:
            query_params["per_page"] = str(int(per_page))
        page = parameters.get("page")
        if page is not None:
            query_params["page"] = str(int(page))
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
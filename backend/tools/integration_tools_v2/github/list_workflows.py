from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GithubListWorkflowsTool(BaseTool):
    name = "github_list_workflows"
    description = "List all workflows in a GitHub repository. Returns workflow details including ID, name, path, state, and badge URL."
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
            context_token_keys=("apiKey",),
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
                    "description": "Repository owner (user or organization)",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
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
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows"
        
        query_params: Dict[str, int] = {}
        per_page = parameters.get("per_page")
        if per_page is not None:
            query_params["per_page"] = int(per_page)
        page = parameters.get("page")
        if page is not None:
            query_params["page"] = int(page)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200]:
                    data = response.json()
                    workflows = data.get("workflows", [])
                    items = [
                        {
                            **workflow,
                            "deleted_at": workflow.get("deleted_at"),
                        }
                        for workflow in workflows
                    ]
                    output_data = {
                        "total_count": data.get("total_count"),
                        "items": items,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
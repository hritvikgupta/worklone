from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubListIssueCommentsTool(BaseTool):
    name = "github_list_issue_comments"
    description = "List all comments on a GitHub issue"
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
                "issue_number": {
                    "type": "integer",
                    "description": "Issue number",
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
            "required": ["owner", "repo", "issue_number"],
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
        
        base_url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/issues/{parameters['issue_number']}/comments"
        request_params: Dict[str, Any] = {}
        if parameters.get("since"):
            request_params["since"] = parameters["since"]
        if "per_page" in parameters and parameters["per_page"] is not None:
            request_params["per_page"] = int(parameters["per_page"])
        if "page" in parameters and parameters["page"] is not None:
            request_params["page"] = int(parameters["page"])
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=request_params)
                
                if response.status_code in [200]:
                    comments = response.json()
                    data = {
                        "items": comments or [],
                        "count": len(comments or []),
                    }
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubUpdateMilestoneTool(BaseTool):
    name = "github_update_milestone"
    description = "Update a milestone in a repository"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_API_KEY",
                description="GitHub API token",
                env_var="GITHUB_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("GITHUB_API_KEY",),
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
                "milestone_number": {
                    "type": "number",
                    "description": "Milestone number to update",
                },
                "title": {
                    "type": "string",
                    "description": "New milestone title",
                },
                "state": {
                    "type": "string",
                    "description": "New state: open or closed",
                },
                "description": {
                    "type": "string",
                    "description": "New description",
                },
                "due_on": {
                    "type": "string",
                    "description": "New due date (ISO 8601 format)",
                },
            },
            "required": ["owner", "repo", "milestone_number"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/milestones/{parameters['milestone_number']}"
        
        body = {}
        for field in ("title", "state", "description", "due_on"):
            if field in parameters:
                body[field] = parameters[field]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
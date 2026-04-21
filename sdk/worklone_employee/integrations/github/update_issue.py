from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubUpdateIssueTool(BaseTool):
    name = "github_update_issue"
    description = "Update an existing issue in a GitHub repository"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
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
                "issue_number": {
                    "type": "number",
                    "description": "Issue number",
                },
                "title": {
                    "type": "string",
                    "description": "New issue title",
                },
                "body": {
                    "type": "string",
                    "description": "New issue description/body",
                },
                "state": {
                    "type": "string",
                    "description": "Issue state (open or closed)",
                },
                "labels": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Array of label names (replaces all existing labels)",
                },
                "assignees": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Array of usernames (replaces all existing assignees)",
                },
            },
            "required": ["owner", "repo", "issue_number"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/issues/{parameters['issue_number']}"
        
        body: Dict[str, Any] = {}
        if parameters.get("title") is not None:
            body["title"] = parameters["title"]
        if parameters.get("body") is not None:
            body["body"] = parameters["body"]
        if parameters.get("state") is not None:
            body["state"] = parameters["state"]
        if parameters.get("labels") is not None:
            body["labels"] = parameters["labels"]
        if parameters.get("assignees") is not None:
            body["assignees"] = parameters["assignees"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
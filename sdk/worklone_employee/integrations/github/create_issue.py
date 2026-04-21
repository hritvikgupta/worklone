from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubCreateIssueTool(BaseTool):
    name = "github_create_issue"
    description = "Create a new issue in a GitHub repository"
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
                "title": {
                    "type": "string",
                    "description": "Issue title",
                },
                "body": {
                    "type": "string",
                    "description": "Issue description/body",
                },
                "assignees": {
                    "type": "string",
                    "description": "Comma-separated list of usernames to assign to this issue",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names to add to this issue",
                },
                "milestone": {
                    "type": "number",
                    "description": "Milestone number to associate with this issue",
                },
            },
            "required": ["owner", "repo", "title"],
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
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        url = f"https://api.github.com/repos/{owner}/{repo}/issues"
        
        body = {
            "title": parameters["title"],
        }
        if parameters.get("body"):
            body["body"] = parameters["body"]
        if parameters.get("assignees"):
            assignees_array = [a.strip() for a in parameters["assignees"].split(",") if a.strip()]
            if assignees_array:
                body["assignees"] = assignees_array
        if parameters.get("labels"):
            labels_array = [l.strip() for l in parameters["labels"].split(",") if l.strip()]
            if labels_array:
                body["labels"] = labels_array
        if parameters.get("milestone"):
            body["milestone"] = parameters["milestone"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubRequestReviewersTool(BaseTool):
    name = "github_request_reviewers"
    description = "Request reviewers for a pull request"
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
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "github",
            context=context,
            context_token_keys=("api_key",),
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
                "pullNumber": {
                    "type": "number",
                    "description": "Pull request number",
                },
                "reviewers": {
                    "type": "string",
                    "description": "Comma-separated list of user logins to request reviews from",
                },
                "team_reviewers": {
                    "type": "string",
                    "description": "Comma-separated list of team slugs to request reviews from",
                },
            },
            "required": ["owner", "repo", "pullNumber", "reviewers"],
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
        pull_number = parameters["pullNumber"]
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers"
        
        reviewers_list = parameters["reviewers"].split(",")
        reviewers_array = [r.strip() for r in reviewers_list if r.strip()]
        
        body = {
            "reviewers": reviewers_array,
        }
        
        team_reviewers = parameters.get("team_reviewers")
        if team_reviewers:
            teams_list = team_reviewers.split(",")
            team_array = [t.strip() for t in teams_list if t.strip()]
            if team_array:
                body["team_reviewers"] = team_array
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
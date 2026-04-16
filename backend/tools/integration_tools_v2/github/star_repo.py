from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubStarRepoTool(BaseTool):
    name = "github_star_repo"
    description = "Star a repository"
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
            context_token_keys=("github_token",),
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
            },
            "required": ["owner", "repo"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        url = f"https://api.github.com/user/starred/{owner}/{repo}"
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "Content-Length": "0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers)
                
                if response.status_code == 204:
                    data = {
                        "starred": True,
                        "owner": owner,
                        "repo": repo,
                    }
                    return ToolResult(
                        success=True,
                        output=f"Successfully starred {owner}/{repo}",
                        data=data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
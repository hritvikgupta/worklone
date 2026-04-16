from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubCreateCommentReactionTool(BaseTool):
    name = "github_create_comment_reaction"
    description = "Add a reaction to an issue comment"
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
                "comment_id": {
                    "type": "number",
                    "description": "Comment ID",
                },
                "content": {
                    "type": "string",
                    "description": "Reaction type: +1 (thumbs up), -1 (thumbs down), laugh, confused, heart, hooray, rocket, eyes",
                    "enum": ["+1", "-1", "laugh", "confused", "heart", "hooray", "rocket", "eyes"],
                },
            },
            "required": ["owner", "repo", "comment_id", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.squirrel-girl-preview+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        comment_id = parameters["comment_id"]
        content = parameters["content"]
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/comments/{comment_id}/reactions"
        
        json_body = {
            "content": content,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
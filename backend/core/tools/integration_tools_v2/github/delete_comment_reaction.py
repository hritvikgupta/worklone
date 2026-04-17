from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitHubDeleteCommentReactionTool(BaseTool):
    name = "github_delete_comment_reaction"
    description = "Remove a reaction from an issue comment"
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
        token = None
        if context:
            token = context.get("apiKey")
        if token is None:
            token = os.getenv("GITHUB_API_KEY")
        if self._is_placeholder_token(token or ""):
            return ""
        return token

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
                "reaction_id": {
                    "type": "number",
                    "description": "Reaction ID to delete",
                },
            },
            "required": ["owner", "repo", "comment_id", "reaction_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="GitHub API token not configured.")

        headers = {
            "Accept": "application/vnd.github.squirrel-girl-preview+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        owner = parameters["owner"]
        repo = parameters["repo"]
        comment_id = parameters["comment_id"]
        reaction_id = parameters["reaction_id"]
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/comments/{comment_id}/reactions/{reaction_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                deleted = response.status_code == 204
                output_data = {
                    "deleted": deleted,
                    "reaction_id": reaction_id,
                }

                if deleted:
                    return ToolResult(success=True, output="", data=output_data)
                else:
                    return ToolResult(
                        success=False, output="", error=response.text, data=output_data
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
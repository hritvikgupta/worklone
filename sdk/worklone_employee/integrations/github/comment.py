from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GitHubCommentTool(BaseTool):
    name = "github_comment"
    description = "Create comments on GitHub PRs"
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
            context_token_keys=("apiKey",),
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
                "body": {
                    "type": "string",
                    "description": "Comment content",
                },
                "pullNumber": {
                    "type": "number",
                    "description": "Pull request number",
                },
                "path": {
                    "type": "string",
                    "description": "File path for review comment",
                },
                "position": {
                    "type": "number",
                    "description": "Line number for review comment",
                },
                "commentType": {
                    "type": "string",
                    "description": "Type of comment (pr_comment or file_comment)",
                },
                "line": {
                    "type": "number",
                    "description": "Line number for review comment",
                },
                "side": {
                    "type": "string",
                    "description": "Side of the diff (LEFT or RIGHT)",
                    "default": "RIGHT",
                },
                "commitId": {
                    "type": "string",
                    "description": "The SHA of the commit to comment on",
                },
            },
            "required": ["owner", "repo", "body", "pullNumber"],
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
        body_content = parameters["body"]
        path = parameters.get("path")
        comment_type = parameters.get("commentType")
        line = parameters.get("line")
        position = parameters.get("position")
        side = parameters.get("side", "RIGHT")
        commit_id = parameters.get("commitId")

        if path:
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/comments"
        else:
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/reviews"

        if comment_type == "file_comment":
            request_body = {
                "body": body_content,
                "commit_id": commit_id,
                "path": path,
                "line": line or position,
                "side": side,
            }
        else:
            request_body = {
                "body": body_content,
                "event": "COMMENT",
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=request_body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
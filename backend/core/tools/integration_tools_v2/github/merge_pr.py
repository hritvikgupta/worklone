from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubMergePRTool(BaseTool):
    name = "github_merge_pr"
    description = "Merge a pull request in a GitHub repository"
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
                "pullNumber": {
                    "type": "number",
                    "description": "Pull request number",
                },
                "commit_title": {
                    "type": "string",
                    "description": "Title for the merge commit",
                },
                "commit_message": {
                    "type": "string",
                    "description": "Extra detail to append to merge commit message",
                },
                "merge_method": {
                    "type": "string",
                    "description": "Merge method: merge, squash, or rebase",
                },
            },
            "required": ["owner", "repo", "pullNumber"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        owner = parameters["owner"]
        repo = parameters["repo"]
        pull_number = int(parameters["pullNumber"])
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/merge"

        body: Dict[str, Any] = {}
        for field in ("commit_title", "commit_message", "merge_method"):
            if field in parameters:
                body[field] = parameters[field]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code == 200:
                    parsed = response.json()
                    data = {
                        "sha": parsed.get("sha"),
                        "merged": parsed.get("merged"),
                        "message": parsed.get("message"),
                    }
                    return ToolResult(success=True, output="", data=data)
                elif response.status_code == 405:
                    try:
                        parsed = response.json()
                        message = parsed.get("message", "Pull request is not mergeable")
                        data = {
                            "sha": None,
                            "merged": False,
                            "message": message,
                        }
                        return ToolResult(
                            success=False,
                            output="",
                            error=message,
                            data=data,
                        )
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=response.text)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
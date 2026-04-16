from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubRemoveLabelTool(BaseTool):
    name = "github_remove_label"
    description = "Remove a label from an issue in a GitHub repository"
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
                    "type": "number",
                    "description": "Issue number",
                },
                "name": {
                    "type": "string",
                    "description": "Label name to remove",
                },
            },
            "required": ["owner", "repo", "issue_number", "name"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        owner = parameters["owner"]
        repo = parameters["repo"]
        issue_number = parameters["issue_number"]
        name = parameters["name"]

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/labels/{quote(name)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

            labels_data = []
            if response.status_code == 200:
                try:
                    labels_data = response.json()
                except Exception:
                    pass

            items = []
            if isinstance(labels_data, list):
                items = [
                    {
                        **label,
                        "description": label.get("description"),
                    }
                    for label in labels_data
                ]

            data = {
                "items": items,
                "count": len(items),
            }

            remaining_text = f"{len(items)} labels remaining" if items else "No labels remaining"
            message = f'Label "{name}" removed from issue #{issue_number} in {owner}/{repo}. {remaining_text}.'

            return ToolResult(success=True, output=message, data=data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
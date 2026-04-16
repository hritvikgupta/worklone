from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubPrTool(BaseTool):
    name = "GitHub PR Reader"
    description = "Fetch PR details including diff and files changed"
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
            context_token_keys=("apiKey", "GITHUB_ACCESS_TOKEN"),
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
        }
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        pull_number = parameters["pullNumber"]
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                pr = response.json()
                
                files_url = f"https://api.github.com/repos/{pr['base']['repo']['owner']['login']}/{pr['base']['repo']['name']}/pulls/{pr['number']}/files"
                files_response = await client.get(files_url, headers=headers)
                
                files = []
                if files_response.status_code == 200:
                    try:
                        files = files_response.json()
                    except Exception:
                        files = []
                
                output_dict = {
                    "id": pr.get("id"),
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "html_url": pr["html_url"],
                    "diff_url": pr["diff_url"],
                    "body": pr.get("body"),
                    "user": pr.get("user"),
                    "head": pr.get("head"),
                    "base": pr.get("base"),
                    "merged": pr.get("merged"),
                    "mergeable": pr.get("mergeable"),
                    "merged_by": pr.get("merged_by"),
                    "comments": pr["comments"],
                    "review_comments": pr["review_comments"],
                    "commits": pr["commits"],
                    "additions": pr["additions"],
                    "deletions": pr["deletions"],
                    "changed_files": pr["changed_files"],
                    "created_at": pr["created_at"],
                    "updated_at": pr["updated_at"],
                    "closed_at": pr.get("closed_at"),
                    "merged_at": pr.get("merged_at"),
                    "files": files,
                }
                
                body_summary = pr.get("body", "No description")
                if len(body_summary) > 500:
                    body_summary = body_summary[:500] + "..."
                
                content = f"""PR #{pr['number']}: "{pr['title']}" ({pr['state']})
Created: {pr['created_at']}, Updated: {pr['updated_at']}
Description: {body_summary}
Files changed: {len(files)}
Additions: {pr.get('additions', 0)}, Deletions: {pr.get('deletions', 0)}
URL: {pr['html_url']}"""
                
                return ToolResult(success=True, output=content, data=output_dict)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
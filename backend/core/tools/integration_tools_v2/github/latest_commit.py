from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GithubLatestCommitTool(BaseTool):
    name = "github_latest_commit"
    description = "Retrieve the latest commit from a GitHub repository"
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
            context_token_keys=("GITHUB_ACCESS_TOKEN", "provider_token", "apiKey"),
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
                    "description": "Repository owner (user or organization)",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch name (defaults to the repository's default branch)",
                },
            },
            "required": ["owner", "repo"],
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
        branch = parameters.get("branch")
        ref = branch or "HEAD"
        url = f"https://api.github.com/repos/{owner}/{repo}/commits/{ref}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    try:
                        error_data = response.json()
                    except Exception:
                        error_data = {}
                    error_msg = error_data.get("message", f"GitHub API error: {response.status_code} - {response.text}")
                    return ToolResult(success=False, output="", error=error_msg)
                
                data = response.json()
                
                commit_author = data["commit"]["author"]
                content = f'Latest commit: "{data["commit"]["message"]}" by {commit_author["name"]} on {commit_author["date"]}. SHA: {data["sha"]}'
                
                files = data.get("files", [])
                file_details = []
                for file in files:
                    file_detail = {
                        "filename": file["filename"],
                        "additions": file["additions"],
                        "deletions": file["deletions"],
                        "changes": file["changes"],
                        "status": file["status"],
                        "raw_url": file.get("raw_url"),
                        "blob_url": file.get("blob_url"),
                        "patch": file.get("patch"),
                        "content": None,
                    }
                    if file["status"] != "removed" and file.get("raw_url"):
                        try:
                            raw_response = await client.get(file["raw_url"], headers=headers)
                            if raw_response.status_code == 200:
                                file_detail["content"] = raw_response.text
                        except Exception:
                            pass
                    file_details.append(file_detail)
                
                author_obj = data.get("author")
                committer_obj = data.get("committer")
                metadata = {
                    "sha": data["sha"],
                    "html_url": data["html_url"],
                    "commit_message": data["commit"]["message"],
                    "author": {
                        "name": data["commit"]["author"]["name"],
                        "login": author_obj["login"] if author_obj else "Unknown",
                        "avatar_url": author_obj.get("avatar_url", "") if author_obj else "",
                        "html_url": author_obj.get("html_url", "") if author_obj else "",
                    },
                    "committer": {
                        "name": data["commit"]["committer"]["name"],
                        "login": committer_obj["login"] if committer_obj else "Unknown",
                        "avatar_url": committer_obj.get("avatar_url", "") if committer_obj else "",
                        "html_url": committer_obj.get("html_url", "") if committer_obj else "",
                    },
                }
                stats = data.get("stats")
                if stats:
                    metadata["stats"] = {
                        "additions": stats["additions"],
                        "deletions": stats["deletions"],
                        "total": stats.get("total"),
                    }
                if file_details:
                    metadata["files"] = file_details
                
                output_data = {"content": content, "metadata": metadata}
                return ToolResult(success=True, output=content, data=output_data)
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
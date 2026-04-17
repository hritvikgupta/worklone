from typing import Any, Dict, List
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitHubGetTreeTool(BaseTool):
    name = "github_get_tree"
    description = "Get the contents of a directory in a GitHub repository. Returns a list of files and subdirectories. Use empty path or omit to get root directory contents."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_API_KEY",
                description="GitHub Personal Access Token",
                env_var="GITHUB_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = (context or {}).get("GITHUB_API_KEY")
        token = token or os.getenv("GITHUB_API_KEY")
        if self._is_placeholder_token(token or ""):
            return ""
        return token

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
                "path": {
                    "type": "string",
                    "description": 'Directory path (e.g., "src/components"). Leave empty for root directory.',
                },
                "ref": {
                    "type": "string",
                    "description": "Branch name, tag, or commit SHA (defaults to repository default branch)",
                },
            },
            "required": ["owner", "repo"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="GitHub API key not configured.")
        
        path = parameters.get("path", "")
        owner = parameters["owner"]
        repo = parameters["repo"]
        ref = parameters.get("ref")
        
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        if ref:
            url += f"?ref={ref}"
        
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception as json_err:
                        return ToolResult(success=False, output="", error=f"Invalid JSON response: {str(json_err)}")
                    
                    if not isinstance(data, list):
                        return ToolResult(
                            success=False,
                            output={"items": [], "count": 0},
                            error="Path points to a file. Use github_get_file_content to get file contents.",
                        )
                    
                    items: List[Dict[str, Any]] = []
                    for item in data:
                        items.append({
                            "name": item.get("name"),
                            "path": item.get("path"),
                            "sha": item.get("sha"),
                            "size": item.get("size"),
                            "type": item.get("type"),
                            "html_url": item.get("html_url"),
                            "download_url": item.get("download_url") or None,
                            "git_url": item.get("git_url"),
                            "url": item.get("url"),
                            "_links": item.get("_links"),
                        })
                    
                    output_data = {
                        "items": items,
                        "count": len(items),
                    }
                    return ToolResult(success=True, output=output_data, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
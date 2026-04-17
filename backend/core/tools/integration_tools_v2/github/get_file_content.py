from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubGetFileContentTool(BaseTool):
    name = "github_get_file_content"
    description = "Get the content of a file from a GitHub repository. Supports files up to 1MB. Content is returned decoded and human-readable."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITHUB_ACCESS_TOKEN",
                description="GitHub Personal Access Token",
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

    def _get_file_extension(self, name: str) -> str:
        parts = name.rsplit(".", 1)
        return parts[-1].lower() if len(parts) > 1 else ""

    def _get_mime_type_from_extension(self, extension: str) -> str:
        mime_map = {
            "txt": "text/plain",
            "html": "text/html",
            "htm": "text/html",
            "css": "text/css",
            "js": "application/javascript",
            "ts": "application/typescript",
            "jsx": "text/jsx",
            "tsx": "text/tsx",
            "py": "text/x-python",
            "json": "application/json",
            "md": "text/markdown",
            "yaml": "text/yaml",
            "yml": "text/yaml",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "pdf": "application/pdf",
            "zip": "application/zip",
            "tar": "application/x-tar",
            "gz": "application/gzip",
        }
        return mime_map.get(extension, "application/octet-stream")

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
                    "description": "Path to the file in the repository (e.g., \"src/index.ts\")",
                },
                "ref": {
                    "type": "string",
                    "description": "Branch name, tag, or commit SHA (defaults to repository default branch)",
                },
            },
            "required": ["owner", "repo", "path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        owner = parameters["owner"]
        repo = parameters["repo"]
        path = parameters["path"]
        ref = parameters.get("ref")
        
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        if ref:
            url += f"?ref={ref}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if isinstance(data, list):
                        return ToolResult(
                            success=False,
                            output="",
                            error="Path points to a directory. Use github_get_tree to list directory contents."
                        )
                    
                    content = data.get("content")
                    encoding = data.get("encoding")
                    decoded_content = None
                    if content and encoding == "base64":
                        content_clean = content.replace("\n", "")
                        try:
                            decoded_content = base64.b64decode(content_clean).decode("utf-8")
                        except:
                            decoded_content = content
                    
                    file_info = None
                    if content and encoding == "base64" and data.get("name"):
                        base64_data = content.replace("\n", "")
                        extension = self._get_file_extension(data["name"])
                        mime_type = self._get_mime_type_from_extension(extension)
                        file_info = {
                            "name": data["name"],
                            "mimeType": mime_type,
                            "data": base64_data,
                            "size": data.get("size", 0),
                        }
                    
                    output_data = {
                        "name": data.get("name"),
                        "path": data.get("path"),
                        "sha": data.get("sha"),
                        "size": data.get("size"),
                        "type": data.get("type"),
                        "content": decoded_content or content or None,
                        "encoding": data.get("encoding"),
                        "html_url": data.get("html_url"),
                        "download_url": data.get("download_url") or None,
                        "git_url": data.get("git_url"),
                        "_links": data.get("_links"),
                        "file": file_info,
                    }
                    
                    content_preview = output_data["content"]
                    if content_preview and isinstance(content_preview, str) and len(content_preview) > 500:
                        content_preview = content_preview[:500] + "\n\n[Content truncated. Full content available in data.content]"
                    
                    output_str = f"""File: {output_data.get('name', 'Unknown')}
Path: {output_data.get('path', '')}
Size: {output_data.get('size', 0)} bytes
Type: {output_data.get('type', '')}
SHA: {output_data.get('sha', '')}

Content Preview:
{content_preview}"""
                    
                    return ToolResult(success=True, output=output_str, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
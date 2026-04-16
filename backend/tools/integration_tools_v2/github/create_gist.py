from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubCreateGistTool(BaseTool):
    name = "github_create_gist"
    description = "Create a new gist with one or more files"
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
                "description": {
                    "type": "string",
                    "description": "Description of the gist",
                },
                "files": {
                    "type": "object",
                    "description": 'JSON object with filenames as keys and content as values. Example: {"file.txt": {"content": "Hello"}}',
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "File content"
                            }
                        },
                        "required": ["content"],
                    },
                },
                "public": {
                    "type": "boolean",
                    "description": "Whether the gist is public (default: false)",
                },
            },
            "required": ["files"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        body = {
            "description": parameters.get("description"),
            "public": parameters.get("public", False),
            "files": parameters["files"],
        }
        url = "https://api.github.com/gists"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
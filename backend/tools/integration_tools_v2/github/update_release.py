from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitHubUpdateReleaseTool(BaseTool):
    name = "github_update_release"
    description = "Update an existing GitHub release. Modify tag name, target commit, title, description, draft status, or prerelease status."
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
                "owner": {
                    "type": "string",
                    "description": "Repository owner (user or organization)",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository name",
                },
                "release_id": {
                    "type": "number",
                    "description": "The unique identifier of the release",
                },
                "tag_name": {
                    "type": "string",
                    "description": "The name of the tag",
                },
                "target_commitish": {
                    "type": "string",
                    "description": "Specifies the commitish value for where the tag is created from",
                },
                "name": {
                    "type": "string",
                    "description": "The name of the release",
                },
                "body": {
                    "type": "string",
                    "description": "Text describing the contents of the release (markdown supported)",
                },
                "draft": {
                    "type": "boolean",
                    "description": "true to set as draft, false to publish",
                },
                "prerelease": {
                    "type": "boolean",
                    "description": "true to identify as a prerelease, false for a full release",
                },
            },
            "required": ["owner", "repo", "release_id"],
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
        
        url = f"https://api.github.com/repos/{parameters['owner']}/{parameters['repo']}/releases/{parameters['release_id']}"
        
        body = {}
        if parameters.get("tag_name"):
            body["tag_name"] = parameters["tag_name"]
        if parameters.get("target_commitish"):
            body["target_commitish"] = parameters["target_commitish"]
        if "name" in parameters:
            body["name"] = parameters["name"]
        if "body" in parameters:
            body["body"] = parameters["body"]
        if "draft" in parameters:
            body["draft"] = parameters["draft"]
        if "prerelease" in parameters:
            body["prerelease"] = parameters["prerelease"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
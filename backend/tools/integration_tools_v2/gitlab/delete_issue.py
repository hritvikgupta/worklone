from typing import Any, Dict
import httpx
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitLabDeleteIssueTool(BaseTool):
    name = "gitlab_delete_issue"
    description = "Delete an issue from a GitLab project"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GITLAB_ACCESS_TOKEN",
                description="GitLab Personal Access Token",
                env_var="GITLAB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "gitlab",
            context=context,
            context_token_keys=("GITLAB_ACCESS_TOKEN",),
            env_token_keys=("GITLAB_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or URL-encoded path",
                },
                "issueIid": {
                    "type": "number",
                    "description": "Issue internal ID (IID)",
                },
            },
            "required": ["projectId", "issueIid"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "PRIVATE-TOKEN": access_token,
        }
        
        project_id = parameters["projectId"]
        issue_iid = parameters["issueIid"]
        encoded_id = urllib.parse.quote(str(project_id))
        url = f"https://gitlab.com/api/v4/projects/{encoded_id}/issues/{issue_iid}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except:
                        data = {"success": True}
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"GitLab API error: {response.status_code} {error_text}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
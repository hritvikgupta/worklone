from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitLabCreateMergeRequestNoteTool(BaseTool):
    name = "GitLab Create Merge Request Comment"
    description = "Add a comment to a GitLab merge request"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="access_token",
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
            context_token_keys=("accessToken",),
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
                "mergeRequestIid": {
                    "type": "number",
                    "description": "Merge request internal ID (IID)",
                },
                "body": {
                    "type": "string",
                    "description": "Comment body (Markdown supported)",
                },
            },
            "required": ["projectId", "mergeRequestIid", "body"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "PRIVATE-TOKEN": access_token,
        }
        
        project_id = parameters["projectId"]
        merge_request_iid = parameters["mergeRequestIid"]
        body = parameters["body"]
        encoded_id = quote(str(project_id))
        url = f"https://gitlab.com/api/v4/projects/{encoded_id}/merge_requests/{merge_request_iid}/notes"
        json_body = {"body": body}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
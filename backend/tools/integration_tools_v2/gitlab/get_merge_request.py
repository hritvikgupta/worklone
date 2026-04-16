from typing import Any, Dict
import httpx
import os
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitLabGetMergeRequestTool(BaseTool):
    name = "gitlab_get_merge_request"
    description = "Get details of a specific GitLab merge request"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessToken",
                description="GitLab Personal Access Token",
                env_var="GITLAB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        access_token = None
        if context:
            access_token = context.get("accessToken")
        if not access_token:
            access_token = os.getenv("GITLAB_ACCESS_TOKEN")
        return access_token or ""

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
            },
            "required": ["projectId", "mergeRequestIid"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "PRIVATE-TOKEN": access_token,
        }
        
        project_id = quote(str(parameters["projectId"]))
        merge_request_iid = parameters["mergeRequestIid"]
        url = f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{merge_request_iid}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=f"GitLab API error: {response.status_code} {response.text}")
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
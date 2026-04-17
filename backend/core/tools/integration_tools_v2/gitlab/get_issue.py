from typing import Any, Dict
import httpx
import os
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitLabGetIssueTool(BaseTool):
    name = "gitlab_get_issue"
    description = "Get details of a specific GitLab issue"
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
        token = context.get("accessToken") if context else None
        token = token or os.getenv("GITLAB_ACCESS_TOKEN")
        return token

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
                    "description": "Issue number within the project (the # shown in GitLab UI)",
                },
            },
            "required": ["projectId", "issueIid"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        project_id = parameters["projectId"]
        issue_iid = parameters["issueIid"]
        encoded_project_id = urllib.parse.quote(str(project_id))
        url = f"https://gitlab.com/api/v4/projects/{encoded_project_id}/issues/{issue_iid}"
        
        headers = {
            "PRIVATE-TOKEN": access_token,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
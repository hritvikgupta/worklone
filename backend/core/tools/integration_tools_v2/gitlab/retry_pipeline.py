from typing import Any, Dict
import httpx
import os
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitLabRetryPipelineTool(BaseTool):
    name = "gitlab_retry_pipeline"
    description = "Retry a failed GitLab pipeline"
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

    def _resolve_access_token(self, context: dict | None) -> str:
        token = (context or {}).get("accessToken")
        token = token or os.getenv("GITLAB_ACCESS_TOKEN", "")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or URL-encoded path",
                },
                "pipelineId": {
                    "type": "number",
                    "description": "Pipeline ID",
                },
            },
            "required": ["projectId", "pipelineId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "PRIVATE-TOKEN": access_token,
        }
        
        project_id = parameters["projectId"]
        encoded_id = urllib.parse.quote(str(project_id), safe="-_.!~*'()")
        pipeline_id = parameters["pipelineId"]
        url = f"https://gitlab.com/api/v4/projects/{encoded_id}/pipelines/{pipeline_id}/retry"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=f"GitLab API error: {response.status_code} {response.text}")
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
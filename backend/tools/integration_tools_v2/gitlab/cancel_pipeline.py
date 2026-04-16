from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitLabCancelPipelineTool(BaseTool):
    name = "gitlab_cancel_pipeline"
    description = "Cancel a running GitLab pipeline"
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
        return (context or {}).get("accessToken") or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or URL-encoded path",
                },
                "pipelineId": {
                    "type": "integer",
                    "description": "Pipeline ID",
                },
            },
            "required": ["projectId", "pipelineId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "PRIVATE-TOKEN": access_token,
        }
        
        project_id = str(parameters["projectId"])
        pipeline_id = parameters["pipelineId"]
        encoded_project_id = quote(project_id)
        url = f"https://gitlab.com/api/v4/projects/{encoded_project_id}/pipelines/{pipeline_id}/cancel"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"GitLab API error: {response.status_code} {error_text}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
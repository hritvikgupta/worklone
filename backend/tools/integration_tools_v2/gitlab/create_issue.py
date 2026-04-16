from typing import Any, Dict
import httpx
import os
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitLabCreateIssueTool(BaseTool):
    name = "gitlab_create_issue"
    description = "Create a new issue in a GitLab project"
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
        token = (context or {}).get("accessToken")
        if self._is_placeholder_token(token or ""):
            token = os.getenv("GITLAB_ACCESS_TOKEN")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Project ID or URL-encoded path",
                },
                "title": {
                    "type": "string",
                    "description": "Issue title",
                },
                "description": {
                    "type": "string",
                    "description": "Issue description (Markdown supported)",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names",
                },
                "assigneeIds": {
                    "type": "array",
                    "description": "Array of user IDs to assign",
                    "items": {
                        "type": "integer",
                    },
                },
                "milestoneId": {
                    "type": "integer",
                    "description": "Milestone ID to assign",
                },
                "dueDate": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format",
                },
                "confidential": {
                    "type": "boolean",
                    "description": "Whether the issue is confidential",
                },
            },
            "required": ["projectId", "title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "PRIVATE-TOKEN": access_token,
        }
        
        encoded_project_id = urllib.parse.quote(str(parameters["projectId"]))
        url = f"https://gitlab.com/api/v4/projects/{encoded_project_id}/issues"
        
        body: Dict[str, Any] = {
            "title": parameters["title"],
        }
        if parameters.get("description"):
            body["description"] = parameters["description"]
        if parameters.get("labels"):
            body["labels"] = parameters["labels"]
        if parameters.get("assigneeIds"):
            body["assignee_ids"] = parameters["assigneeIds"]
        if parameters.get("milestoneId") is not None:
            body["milestone_id"] = parameters["milestoneId"]
        if parameters.get("dueDate"):
            body["due_date"] = parameters["dueDate"]
        if "confidential" in parameters:
            body["confidential"] = parameters["confidential"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
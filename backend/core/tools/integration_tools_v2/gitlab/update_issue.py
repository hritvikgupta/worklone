from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitlabUpdateIssueTool(BaseTool):
    name = "gitlab_update_issue"
    description = "Update an existing issue in a GitLab project"
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
                "title": {
                    "type": "string",
                    "description": "New issue title",
                },
                "description": {
                    "type": "string",
                    "description": "New issue description (Markdown supported)",
                },
                "stateEvent": {
                    "type": "string",
                    "description": "State event (close or reopen)",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names",
                },
                "assigneeIds": {
                    "type": "array",
                    "description": "Array of user IDs to assign",
                },
                "milestoneId": {
                    "type": "number",
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
            "required": ["projectId", "issueIid"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = context.get("GITLAB_ACCESS_TOKEN") if context else None
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "PRIVATE-TOKEN": access_token,
        }
        
        encoded_project_id = quote(str(parameters["projectId"]))
        url = f"https://gitlab.com/api/v4/projects/{encoded_project_id}/issues/{parameters['issueIid']}"
        
        body: Dict[str, Any] = {}
        if "title" in parameters and parameters["title"]:
            body["title"] = parameters["title"]
        if "description" in parameters:
            body["description"] = parameters["description"]
        if "stateEvent" in parameters and parameters["stateEvent"]:
            body["state_event"] = parameters["stateEvent"]
        if "labels" in parameters:
            body["labels"] = parameters["labels"]
        if "assigneeIds" in parameters:
            body["assignee_ids"] = parameters["assigneeIds"]
        if "milestoneId" in parameters:
            body["milestone_id"] = parameters["milestoneId"]
        if "dueDate" in parameters:
            body["due_date"] = parameters["dueDate"]
        if "confidential" in parameters:
            body["confidential"] = parameters["confidential"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class GitLabCreateMergeRequestTool(BaseTool):
    name = "GitLab Create Merge Request"
    description = "Create a new merge request in a GitLab project"
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
                "sourceBranch": {
                    "type": "string",
                    "description": "Source branch name",
                },
                "targetBranch": {
                    "type": "string",
                    "description": "Target branch name",
                },
                "title": {
                    "type": "string",
                    "description": "Merge request title",
                },
                "description": {
                    "type": "string",
                    "description": "Merge request description (Markdown supported)",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names",
                },
                "assigneeIds": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                    },
                    "description": "Array of user IDs to assign",
                },
                "milestoneId": {
                    "type": "number",
                    "description": "Milestone ID to assign",
                },
                "removeSourceBranch": {
                    "type": "boolean",
                    "description": "Delete source branch after merge",
                },
                "squash": {
                    "type": "boolean",
                    "description": "Squash commits on merge",
                },
                "draft": {
                    "type": "boolean",
                    "description": "Mark as draft (work in progress)",
                },
            },
            "required": ["projectId", "sourceBranch", "targetBranch", "title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Content-Type": "application/json",
            "PRIVATE-TOKEN": access_token,
        }

        encoded_project_id = quote(str(parameters["projectId"]))
        url = f"https://gitlab.com/api/v4/projects/{encoded_project_id}/merge_requests"

        body = {
            "source_branch": parameters["sourceBranch"],
            "target_branch": parameters["targetBranch"],
            "title": parameters["title"],
        }
        if "description" in parameters and parameters["description"]:
            body["description"] = parameters["description"]
        if "labels" in parameters and parameters["labels"]:
            body["labels"] = parameters["labels"]
        if "assigneeIds" in parameters and parameters["assigneeIds"] and len(parameters["assigneeIds"]) > 0:
            body["assignee_ids"] = parameters["assigneeIds"]
        if "milestoneId" in parameters and parameters["milestoneId"]:
            body["milestone_id"] = parameters["milestoneId"]
        if "removeSourceBranch" in parameters:
            body["remove_source_branch"] = parameters["removeSourceBranch"]
        if "squash" in parameters:
            body["squash"] = parameters["squash"]
        if "draft" in parameters:
            body["draft"] = parameters["draft"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
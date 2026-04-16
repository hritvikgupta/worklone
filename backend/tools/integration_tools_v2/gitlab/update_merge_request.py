from typing import Any, Dict
import httpx
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitLabUpdateMergeRequestTool(BaseTool):
    name = "GitLab Update Merge Request"
    description = "Update an existing merge request in a GitLab project"
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
                "mergeRequestIid": {
                    "type": "number",
                    "description": "Merge request internal ID (IID)",
                },
                "title": {
                    "type": "string",
                    "description": "New merge request title",
                },
                "description": {
                    "type": "string",
                    "description": "New merge request description",
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
                    "items": {
                        "type": "number",
                    },
                    "description": "Array of user IDs to assign",
                },
                "milestoneId": {
                    "type": "number",
                    "description": "Milestone ID to assign",
                },
                "targetBranch": {
                    "type": "string",
                    "description": "New target branch",
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
            "required": ["projectId", "mergeRequestIid"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "PRIVATE-TOKEN": access_token,
        }
        
        encoded_id = urllib.parse.quote(str(parameters["projectId"]))
        url = f"https://gitlab.com/api/v4/projects/{encoded_id}/merge_requests/{parameters['mergeRequestIid']}"
        
        body: Dict[str, Any] = {}
        title = parameters.get("title")
        if title:
            body["title"] = title
        description = parameters.get("description")
        if description is not None:
            body["description"] = description
        state_event = parameters.get("stateEvent")
        if state_event:
            body["state_event"] = state_event
        labels = parameters.get("labels")
        if labels is not None:
            body["labels"] = labels
        assignee_ids = parameters.get("assigneeIds")
        if assignee_ids is not None:
            body["assignee_ids"] = assignee_ids
        milestone_id = parameters.get("milestoneId")
        if milestone_id is not None:
            body["milestone_id"] = milestone_id
        target_branch = parameters.get("targetBranch")
        if target_branch:
            body["target_branch"] = target_branch
        remove_source_branch = parameters.get("removeSourceBranch")
        if remove_source_branch is not None:
            body["remove_source_branch"] = remove_source_branch
        squash = parameters.get("squash")
        if squash is not None:
            body["squash"] = squash
        draft = parameters.get("draft")
        if draft is not None:
            body["draft"] = draft
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_msg = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"GitLab API error: {response.status_code} {error_msg}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
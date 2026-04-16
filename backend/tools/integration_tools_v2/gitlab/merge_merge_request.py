from typing import Any, Dict
import httpx
import base64
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitLabMergeMergeRequestTool(BaseTool):
    name = "GitLab Merge Merge Request"
    description = "Merge a merge request in a GitLab project"
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
                "mergeCommitMessage": {
                    "type": "string",
                    "description": "Custom merge commit message",
                },
                "squashCommitMessage": {
                    "type": "string",
                    "description": "Custom squash commit message",
                },
                "squash": {
                    "type": "boolean",
                    "description": "Squash commits before merging",
                },
                "shouldRemoveSourceBranch": {
                    "type": "boolean",
                    "description": "Delete source branch after merge",
                },
                "mergeWhenPipelineSucceeds": {
                    "type": "boolean",
                    "description": "Merge when pipeline succeeds",
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
        
        encoded_project_id = urllib.parse.quote(str(parameters["projectId"]))
        url = f"https://gitlab.com/api/v4/projects/{encoded_project_id}/merge_requests/{parameters['mergeRequestIid']}/merge"
        
        body = {}
        if "mergeCommitMessage" in parameters:
            body["merge_commit_message"] = parameters["mergeCommitMessage"]
        if "squashCommitMessage" in parameters:
            body["squash_commit_message"] = parameters["squashCommitMessage"]
        if "squash" in parameters:
            body["squash"] = parameters["squash"]
        if "shouldRemoveSourceBranch" in parameters:
            body["should_remove_source_branch"] = parameters["shouldRemoveSourceBranch"]
        if "mergeWhenPipelineSucceeds" in parameters:
            body["merge_when_pipeline_succeeds"] = parameters["mergeWhenPipelineSucceeds"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
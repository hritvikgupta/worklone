from typing import Any, Dict
import httpx
import os
from urllib.parse import quote
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitLabCreateIssueNoteTool(BaseTool):
    name = "gitlab_create_issue_comment"
    description = "Add a comment to a GitLab issue"
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
        token = context.get("accessToken") if context else None
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
                "issueIid": {
                    "type": "number",
                    "description": "Issue internal ID (IID)",
                },
                "body": {
                    "type": "string",
                    "description": "Comment body (Markdown supported)",
                },
            },
            "required": ["projectId", "issueIid", "body"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        project_id = parameters["projectId"]
        issue_iid = parameters["issueIid"]
        body = parameters["body"]

        encoded_id = quote(str(project_id), safe="")
        url = f"https://gitlab.com/api/v4/projects/{encoded_id}/issues/{issue_iid}/notes"

        headers = {
            "Content-Type": "application/json",
            "PRIVATE-TOKEN": access_token,
        }

        json_body = {
            "body": body,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(
                        success=False, output="", error=f"GitLab API error ({response.status_code}): {response.text}"
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
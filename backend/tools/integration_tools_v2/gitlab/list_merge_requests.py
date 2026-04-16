from typing import Any, Dict
import httpx
import os
from urllib.parse import quote, urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GitlabListMergeRequestsTool(BaseTool):
    name = "gitlab_list_merge_requests"
    description = "List merge requests in a GitLab project"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="access_token",
                description="GitLab Personal Access Token",
                env_var="GITLAB_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = None
        if context is not None:
            token = context.get("access_token")
        if token is None:
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
                "state": {
                    "type": "string",
                    "description": "Filter by state (opened, closed, merged, all)",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated list of label names",
                },
                "sourceBranch": {
                    "type": "string",
                    "description": "Filter by source branch",
                },
                "targetBranch": {
                    "type": "string",
                    "description": "Filter by target branch",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order by field (created_at, updated_at)",
                },
                "sort": {
                    "type": "string",
                    "description": "Sort direction (asc, desc)",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page (default 20, max 100)",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination",
                },
            },
            "required": ["projectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        project_id = parameters.get("projectId")
        if not project_id:
            return ToolResult(success=False, output="", error="projectId is required.")

        encoded_id = quote(str(project_id))

        query_params: list[tuple[str, str]] = []
        state = parameters.get("state")
        if state:
            query_params.append(("state", state))
        labels = parameters.get("labels")
        if labels:
            query_params.append(("labels", labels))
        source_branch = parameters.get("sourceBranch")
        if source_branch:
            query_params.append(("source_branch", source_branch))
        target_branch = parameters.get("targetBranch")
        if target_branch:
            query_params.append(("target_branch", target_branch))
        order_by = parameters.get("orderBy")
        if order_by:
            query_params.append(("order_by", order_by))
        sort = parameters.get("sort")
        if sort:
            query_params.append(("sort", sort))
        per_page = parameters.get("perPage")
        if per_page:
            query_params.append(("per_page", str(int(per_page))))
        page = parameters.get("page")
        if page:
            query_params.append(("page", str(int(page))))

        query_string = urlencode(query_params) if query_params else ""
        url = f"https://gitlab.com/api/v4/projects/{encoded_id}/merge_requests"
        if query_string:
            url += f"?{query_string}"

        headers = {
            "PRIVATE-TOKEN": access_token,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    merge_requests = response.json()
                    total_str = response.headers.get("X-Total")
                    total = int(total_str) if total_str else len(merge_requests)
                    data = {
                        "mergeRequests": merge_requests,
                        "total": total,
                    }
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_msg = f"GitLab API error ({response.status_code}): {response.text}"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
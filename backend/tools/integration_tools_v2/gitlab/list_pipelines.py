from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class GitLabListPipelinesTool(BaseTool):
    name = "gitlab_list_pipelines"
    description = "List pipelines in a GitLab project"
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
                "ref": {
                    "type": "string",
                    "description": "Filter by ref (branch or tag)",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by status (created, waiting_for_resource, preparing, pending, running, success, failed, canceled, skipped, manual, scheduled)",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order by field (id, status, ref, updated_at, user_id)",
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

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "PRIVATE-TOKEN": access_token,
        }
        
        project_id = parameters["projectId"]
        encoded_project_id = quote(str(project_id))
        base_url = f"https://gitlab.com/api/v4/projects/{encoded_project_id}/pipelines"
        
        query_params: Dict[str, str] = {}
        param_mappings = [
            ("ref", "ref", "ref"),
            ("status", "status", "status"),
            ("orderBy", "orderBy", "order_by"),
            ("sort", "sort", "sort"),
            ("perPage", "perPage", "per_page"),
            ("page", "page", "page"),
        ]
        for param_key, query_key in [(m[0], m[2]) for m in param_mappings]:
            value = parameters.get(param_key)
            if value:
                query_params[query_key] = str(value)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=query_params)
                
                if response.status_code in [200]:
                    data = response.json()
                    total_header = response.headers.get("x-total")
                    total = int(total_header) if total_header else len(data)
                    processed_data = {
                        "pipelines": data,
                        "total": total,
                    }
                    return ToolResult(success=True, output=response.text, data=processed_data)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"GitLab API error: {response.status_code} {response.text}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
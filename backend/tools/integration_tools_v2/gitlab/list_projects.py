from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GitLabListProjectsTool(BaseTool):
    name = "gitlab_list_projects"
    description = "List GitLab projects accessible to the authenticated user"
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

    def _build_query_params(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        query_params: Dict[str, str] = {}
        owned = parameters.get("owned")
        if owned:
            query_params["owned"] = "true"
        membership = parameters.get("membership")
        if membership:
            query_params["membership"] = "true"
        search = parameters.get("search")
        if search:
            query_params["search"] = str(search)
        visibility = parameters.get("visibility")
        if visibility:
            query_params["visibility"] = str(visibility)
        order_by = parameters.get("orderBy")
        if order_by:
            query_params["order_by"] = str(order_by)
        sort_val = parameters.get("sort")
        if sort_val:
            query_params["sort"] = str(sort_val)
        per_page = parameters.get("perPage")
        if per_page:
            query_params["per_page"] = str(per_page)
        page = parameters.get("page")
        if page:
            query_params["page"] = str(page)
        return query_params

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "owned": {
                    "type": "boolean",
                    "description": "Limit to projects owned by the current user",
                },
                "membership": {
                    "type": "boolean",
                    "description": "Limit to projects the current user is a member of",
                },
                "search": {
                    "type": "string",
                    "description": "Search projects by name",
                },
                "visibility": {
                    "type": "string",
                    "description": "Filter by visibility (public, internal, private)",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order by field (id, name, path, created_at, updated_at, last_activity_at)",
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
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "PRIVATE-TOKEN": access_token,
        }

        url = "https://gitlab.com/api/v4/projects"
        query_params = self._build_query_params(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    projects = response.json()
                    total_header = response.headers.get("x-total")
                    total = int(total_header) if total_header else len(projects)
                    data = {
                        "projects": projects,
                        "total": total,
                    }
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_msg = f"GitLab API error ({response.status_code}): {response.text}"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"GitLab API error: {str(e)}")
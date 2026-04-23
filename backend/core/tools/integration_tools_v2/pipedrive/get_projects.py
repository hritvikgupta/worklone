from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveGetProjectsTool(BaseTool):
    name = "pipedrive_get_projects"
    description = "Retrieve all projects or a specific project from Pipedrive"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PIPEDRIVE_ACCESS_TOKEN",
                description="The access token for the Pipedrive API",
                env_var="PIPEDRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Optional: ID of a specific project to retrieve (e.g., \"123\")",
                },
                "status": {
                    "type": "string",
                    "description": "Filter by project status: open, completed, deleted (only for listing all)",
                },
                "limit": {
                    "type": "string",
                    "description": "Number of results to return (e.g., \"50\", default: 100, max: 500, only for listing all)",
                },
                "cursor": {
                    "type": "string",
                    "description": "For pagination, the marker representing the first item on the next page",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        project_id = parameters.get("project_id")
        if project_id:
            url = f"https://api.pipedrive.com/v1/projects/{project_id}"
            query_params = None
        else:
            url = "https://api.pipedrive.com/v1/projects"
            query_params = {
                key: parameters.get(key)
                for key in ["status", "limit", "cursor"]
                if parameters.get(key)
            }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)
                
                resp_data = response.json()
                if not resp_data.get("success"):
                    return ToolResult(
                        success=False,
                        output="",
                        error=resp_data.get("error", "Failed to fetch project(s) from Pipedrive")
                    )
                
                if project_id:
                    transformed = {
                        "project": resp_data.get("data"),
                        "success": True,
                    }
                else:
                    projects = resp_data.get("data", [])
                    additional_data = resp_data.get("additional_data", {})
                    next_cursor = additional_data.get("next_cursor")
                    transformed = {
                        "projects": projects,
                        "total_items": len(projects),
                        "has_more": next_cursor is not None,
                        "next_cursor": next_cursor,
                        "success": True,
                    }
                
                return ToolResult(
                    success=True,
                    output=json.dumps(transformed),
                    data=transformed
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveGetPipelinesTool(BaseTool):
    name = "pipedrive_get_pipelines"
    description = "Retrieve all pipelines from Pipedrive"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PIPEDRIVE_ACCESS_TOKEN",
                description="Access token for the Pipedrive API",
                env_var="PIPEDRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
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
                "sort_by": {
                    "type": "string",
                    "description": "Field to sort by: id, update_time, add_time (default: id)",
                },
                "sort_direction": {
                    "type": "string",
                    "description": "Sorting direction: asc, desc (default: asc)",
                },
                "limit": {
                    "type": "string",
                    "description": "Number of results to return (e.g., \"50\", default: 100, max: 500)",
                },
                "start": {
                    "type": "string",
                    "description": "Pagination start offset (0-based index of the first item to return)",
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
        
        query_params = {}
        for key in ["sort_by", "sort_direction", "limit", "start"]:
            if key in parameters:
                query_params[key] = parameters[key]
        
        url = "https://api.pipedrive.com/v1/pipelines"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if not data.get("success", False):
                    return ToolResult(
                        success=False,
                        output="",
                        error=data.get("error", "Failed to fetch pipelines from Pipedrive")
                    )
                
                pipelines = data.get("data", [])
                additional_data = data.get("additional_data", {})
                pagination = additional_data.get("pagination", {})
                has_more = pagination.get("more_items_in_collection", False)
                next_start = pagination.get("next_start")
                
                transformed = {
                    "pipelines": pipelines,
                    "total_items": len(pipelines),
                    "has_more": has_more,
                    "next_start": next_start,
                    "success": True,
                }
                
                return ToolResult(success=True, output=response.text, data=transformed)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
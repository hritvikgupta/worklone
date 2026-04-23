from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveGetPipelineDealsTool(BaseTool):
    name = "pipedrive_get_pipeline_deals"
    description = "Retrieve all deals in a specific pipeline"
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
            context_token_keys=("provider_token",),
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pipeline_id": {
                    "type": "string",
                    "description": "The ID of the pipeline (e.g., \"1\")",
                },
                "stage_id": {
                    "type": "string",
                    "description": "Filter by specific stage within the pipeline (e.g., \"2\")",
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
            "required": ["pipeline_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        pipeline_id = parameters["pipeline_id"]
        url = f"https://api.pipedrive.com/v1/pipelines/{pipeline_id}/deals"
        query_params: Dict[str, str] = {}
        stage_id = parameters.get("stage_id")
        if stage_id:
            query_params["stage_id"] = stage_id
        limit = parameters.get("limit")
        if limit:
            query_params["limit"] = limit
        start = parameters.get("start")
        if start:
            query_params["start"] = start
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if not data.get("success", False):
                    error_msg = data.get("error") or "Failed to fetch pipeline deals from Pipedrive"
                    return ToolResult(success=False, output="", error=error_msg)
                
                deals = data.get("data", [])
                pagination = data.get("additional_data", {}).get("pagination", {})
                has_more = pagination.get("more_items_in_collection", False)
                next_start = pagination.get("next_start")
                
                transformed = {
                    "deals": deals,
                    "metadata": {
                        "pipeline_id": pipeline_id,
                        "total_items": len(deals),
                        "has_more": has_more,
                        "next_start": next_start,
                    },
                    "success": True,
                }
                output_str = json.dumps(transformed)
                return ToolResult(success=True, output=output_str, data=transformed)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
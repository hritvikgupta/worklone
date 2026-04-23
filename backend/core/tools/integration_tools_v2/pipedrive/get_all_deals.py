from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveGetAllDealsTool(BaseTool):
    name = "pipedrive_get_all_deals"
    description = "Retrieve all deals from Pipedrive with optional filters"
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
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("provider_token",},
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",},
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Only fetch deals with a specific status. Values: open, won, lost. If omitted, all not deleted deals are returned",
                },
                "person_id": {
                    "type": "string",
                    "description": "If supplied, only deals linked to the specified person are returned (e.g., \"456\")",
                },
                "org_id": {
                    "type": "string",
                    "description": "If supplied, only deals linked to the specified organization are returned (e.g., \"789\")",
                },
                "pipeline_id": {
                    "type": "string",
                    "description": "If supplied, only deals in the specified pipeline are returned (e.g., \"1\")",
                },
                "updated_since": {
                    "type": "string",
                    "description": "If set, only deals updated after this time are returned. Format: 2025-01-01T10:20:00Z",
                },
                "limit": {
                    "type": "string",
                    "description": "Number of results to return (e.g., \"50\", default: 100, max: 500)",
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
        
        url = "https://api.pipedrive.com/api/v2/deals"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=parameters)
                
                response_data = response.json()
                
                if response.status_code != 200 or not response_data.get("success"):
                    error_msg = response_data.get("error", "Failed to fetch deals from Pipedrive")
                    return ToolResult(success=False, output="", error=error_msg)
                
                deals = response_data.get("data", [])
                additional_data = response_data.get("additional_data", {})
                next_cursor = additional_data.get("next_cursor")
                has_more = next_cursor is not None
                
                transformed = {
                    "deals": deals,
                    "metadata": {
                        "total_items": len(deals),
                        "has_more": has_more,
                        "next_cursor": next_cursor,
                    },
                    "success": True,
                }
                
                return ToolResult(
                    success=True,
                    output=json.dumps(transformed),
                    data=transformed
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
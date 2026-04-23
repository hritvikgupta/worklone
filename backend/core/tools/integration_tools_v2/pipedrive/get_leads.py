from typing import Any, Dict
import httpx
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveGetLeadsTool(BaseTool):
    name = "pipedrive_get_leads"
    description = "Retrieve all leads or a specific lead from Pipedrive"
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
                "lead_id": {
                    "type": "string",
                    "description": "Optional: ID of a specific lead to retrieve (e.g., \"abc123-def456-ghi789\")",
                },
                "archived": {
                    "type": "string",
                    "description": "Get archived leads instead of active ones (e.g., \"true\" or \"false\")",
                },
                "owner_id": {
                    "type": "string",
                    "description": "Filter by owner user ID (e.g., \"123\")",
                },
                "person_id": {
                    "type": "string",
                    "description": "Filter by person ID (e.g., \"456\")",
                },
                "organization_id": {
                    "type": "string",
                    "description": "Filter by organization ID (e.g., \"789\")",
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

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }
        
        lead_id = parameters.get("lead_id")
        if lead_id:
            url = f"https://api.pipedrive.com/v1/leads/{lead_id}"
        else:
            archived = parameters.get("archived") == "true"
            base_url = "https://api.pipedrive.com/v1/leads/archived" if archived else "https://api.pipedrive.com/v1/leads"
            query_params: dict[str, str] = {}
            for key in ["owner_id", "person_id", "organization_id", "limit", "start"]:
                value = parameters.get(key)
                if value is not None:
                    query_params[key] = str(value)
            if query_params:
                query_string = urlencode(query_params)
                url = f"{base_url}?{query_string}"
            else:
                url = base_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except Exception:
                        return ToolResult(success=False, output="", error="Invalid JSON response")
                    
                    if not data.get("success", False):
                        return ToolResult(
                            success=False,
                            output="",
                            error=data.get("error", "Failed to fetch lead(s) from Pipedrive")
                        )
                    
                    if lead_id:
                        transformed = {
                            "lead": data.get("data"),
                            "success": True,
                        }
                    else:
                        leads = data.get("data", [])
                        additional_data = data.get("additional_data", {})
                        has_more = additional_data.get("more_items_in_collection", False)
                        current_start = additional_data.get("start", 0)
                        current_limit = additional_data.get("limit", len(leads))
                        next_start = current_start + current_limit if has_more else None
                        transformed = {
                            "leads": leads,
                            "total_items": len(leads),
                            "has_more": has_more,
                            "next_start": next_start,
                            "success": True,
                        }
                    
                    output_str = json.dumps(transformed)
                    return ToolResult(success=True, output=output_str, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
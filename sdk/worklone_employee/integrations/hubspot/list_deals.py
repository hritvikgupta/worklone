from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotListDealsTool(BaseTool):
    name = "hubspot_list_deals"
    description = "Retrieve all deals from HubSpot account with pagination support"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUBSPOT_ACCESS_TOKEN",
                description="The access token for the HubSpot API",
                env_var="HUBSPOT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hubspot",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("HUBSPOT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "string",
                    "description": "Maximum number of results per page (max 100, default 10)",
                },
                "after": {
                    "type": "string",
                    "description": "Pagination cursor for next page of results (from previous response)",
                },
                "properties": {
                    "type": "string",
                    "description": 'Comma-separated list of HubSpot property names to return (e.g., "dealname,amount,dealstage")',
                },
                "associations": {
                    "type": "string",
                    "description": 'Comma-separated list of object types to retrieve associated IDs for (e.g., "contacts,companies")',
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
            "Content-Type": "application/json",
        }
        
        url = "https://api.hubapi.com/crm/v3/objects/deals"
        params_dict = {
            "limit": parameters.get("limit"),
            "after": parameters.get("after"),
            "properties": parameters.get("properties"),
            "associations": parameters.get("associations"),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code == 200:
                    data = response.json()
                    deals = data.get("results", [])
                    paging = data.get("paging")
                    has_more = bool(data.get("paging", {}).get("next"))
                    output_dict = {
                        "deals": deals,
                        "paging": paging,
                        "metadata": {
                            "totalReturned": len(deals),
                            "hasMore": has_more,
                        },
                        "success": True,
                    }
                    return ToolResult(success=True, output=json.dumps(output_dict), data=output_dict)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message") or response.text
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
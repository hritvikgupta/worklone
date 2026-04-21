from typing import Any, Dict
import httpx
import base64
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotListLineItemsTool(BaseTool):
    name = "hubspot_list_line_items"
    description = "Retrieve all line items from HubSpot account with pagination support"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUBSPOT_ACCESS_TOKEN",
                description="Access token",
                env_var="HUBSPOT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hubspot",
            context=context,
            context_token_keys=("provider_token",),
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
                    "description": 'Comma-separated list of HubSpot property names to return (e.g., "name,quantity,price,amount")',
                },
                "associations": {
                    "type": "string",
                    "description": 'Comma-separated list of object types to retrieve associated IDs for (e.g., "deals,quotes")',
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
        
        query_params = {}
        for key in ["limit", "after", "properties", "associations"]:
            if key in parameters:
                query_params[key] = parameters[key]
        
        url = "https://api.hubapi.com/crm/v3/objects/line_items"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
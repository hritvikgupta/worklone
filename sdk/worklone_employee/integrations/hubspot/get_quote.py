from typing import Any, Dict
import httpx
import base64
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotGetQuoteTool(BaseTool):
    name = "hubspot_get_quote"
    description = "Retrieve a single quote by ID from HubSpot"
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
                "quoteId": {
                    "type": "string",
                    "description": "The HubSpot quote ID to retrieve",
                },
                "idProperty": {
                    "type": "string",
                    "description": "Property to use as unique identifier. If not specified, uses record ID",
                },
                "properties": {
                    "type": "string",
                    "description": 'Comma-separated list of HubSpot property names to return (e.g., "hs_title,hs_expiration_date,hs_status")',
                },
                "associations": {
                    "type": "string",
                    "description": 'Comma-separated list of object types to retrieve associated IDs for (e.g., "deals,line_items")',
                },
            },
            "required": ["quoteId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        quote_id = parameters.get("quoteId", "").strip()
        if not quote_id:
            return ToolResult(success=False, output="", error="quoteId is required.")
        
        url = f"https://api.hubapi.com/crm/v3/objects/quotes/{quote_id}"
        
        params: dict[str, str] = {}
        if id_property := parameters.get("idProperty"):
            params["idProperty"] = id_property
        if properties := parameters.get("properties"):
            params["properties"] = properties
        if associations := parameters.get("associations"):
            params["associations"] = associations
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    processed_data = {
                        "quote": data,
                        "quoteId": data.get("id"),
                        "success": True,
                    }
                    return ToolResult(success=True, output=response.text, data=processed_data)
                else:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except Exception:
                        pass
                    error_msg = error_data.get("message") or error_data.get("error") or response.text or f"HTTP {response.status_code}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
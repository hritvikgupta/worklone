from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HubspotSearchTicketsTool(BaseTool):
    name = "hubspot_search_tickets"
    description = "Search for tickets in HubSpot using filters, sorting, and queries"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUBSPOT_ACCESS_TOKEN",
                description="Access token for the HubSpot API",
                env_var="HUBSPOT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hubspot",
            context=context,
            context_token_keys=("hubspot_token",),
            env_token_keys=("HUBSPOT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _build_body(self, parameters: dict) -> dict:
        body: dict = {}
        for field_name in ["filterGroups", "sorts", "properties"]:
            if field_name not in parameters:
                continue
            parsed = parameters[field_name]
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON for {field_name}: {str(e)}")
            if isinstance(parsed, list) and parsed:
                body[field_name] = parsed
        if parameters.get("query"):
            body["query"] = parameters["query"]
        if "limit" in parameters:
            body["limit"] = parameters["limit"]
        if parameters.get("after"):
            body["after"] = parameters["after"]
        return body

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filterGroups": {
                    "type": "array",
                    "description": 'Array of filter groups as JSON. Each group contains "filters" array with objects having "propertyName", "operator" (e.g., "EQ", "NEQ", "CONTAINS_TOKEN", "NOT_CONTAINS_TOKEN"), and "value"',
                },
                "sorts": {
                    "type": "array",
                    "description": 'Array of sort objects as JSON with "propertyName" and "direction" ("ASCENDING" or "DESCENDING")',
                },
                "query": {
                    "type": "string",
                    "description": "Search query string to match against ticket subject and other text fields",
                },
                "properties": {
                    "type": "array",
                    "description": 'Array of HubSpot property names to return (e.g., ["subject", "content", "hs_ticket_priority"])',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return (max 200)",
                },
                "after": {
                    "type": "string",
                    "description": "Pagination cursor for next page (from previous response)",
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
        
        url = "https://api.hubapi.com/crm/v3/objects/tickets/search"
        
        try:
            body = self._build_body(parameters)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HubspotSearchDealsTool(BaseTool):
    name = "hubspot_search_deals"
    description = "Search for deals in HubSpot using filters, sorting, and queries"
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
                    "description": "Search query string to match against deal name and other text fields",
                },
                "properties": {
                    "type": "array",
                    "description": 'Array of HubSpot property names to return (e.g., ["dealname", "amount", "dealstage"])',
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

    def _build_body(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        for field in ["filterGroups", "sorts", "properties"]:
            val = parameters.get(field)
            if val:
                parsed = val
                if isinstance(val, str):
                    try:
                        parsed = json.loads(val)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON for {field}: {str(e)}")
                if isinstance(parsed, list) and len(parsed) > 0:
                    body[field] = parsed
        for field in ["query", "limit", "after"]:
            val = parameters.get(field)
            if val is not None:
                body[field] = val
        return body

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.hubapi.com/crm/v3/objects/deals/search"
        body = self._build_body(parameters)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotSearchContactsTool(BaseTool):
    name = "hubspot_search_contacts"
    description = "Search for contacts in HubSpot using filters, sorting, and queries"
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
            context_token_keys=("accessToken",),
            env_token_keys=("HUBSPOT_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def _parse_param(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON for parameter: {str(e)}")
        return value

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filterGroups": {
                    "type": "array",
                    "description": 'Array of filter groups as JSON. Each group contains "filters" array with objects having "propertyName", "operator" (e.g., "EQ", "CONTAINS_TOKEN", "GT"), and "value"',
                },
                "sorts": {
                    "type": "array",
                    "description": 'Array of sort objects as JSON with "propertyName" and "direction" ("ASCENDING" or "DESCENDING")',
                },
                "query": {
                    "type": "string",
                    "description": "Search query string to match against contact name, email, and other text fields",
                },
                "properties": {
                    "type": "array",
                    "description": 'Array of HubSpot property names to return (e.g., ["email", "firstname", "lastname", "phone"])',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return (max 100)",
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
        
        url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
        
        body: Dict[str, Any] = {}
        fg = parameters.get("filterGroups")
        if fg is not None:
            parsed_fg = self._parse_param(fg)
            if isinstance(parsed_fg, list) and len(parsed_fg) > 0:
                body["filterGroups"] = parsed_fg
        s = parameters.get("sorts")
        if s is not None:
            parsed_s = self._parse_param(s)
            if isinstance(parsed_s, list) and len(parsed_s) > 0:
                body["sorts"] = parsed_s
        p = parameters.get("properties")
        if p is not None:
            parsed_p = self._parse_param(p)
            if isinstance(parsed_p, list) and len(parsed_p) > 0:
                body["properties"] = parsed_p
        q = parameters.get("query")
        if q:
            body["query"] = q
        l = parameters.get("limit")
        if l is not None:
            body["limit"] = int(l)
        a = parameters.get("after")
        if a:
            body["after"] = a
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
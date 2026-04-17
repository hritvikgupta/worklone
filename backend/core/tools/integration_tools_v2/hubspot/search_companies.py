from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HubspotSearchCompaniesTool(BaseTool):
    name = "hubspot_search_companies"
    description = "Search for companies in HubSpot using filters, sorting, and queries"
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
            context_token_keys=("hubspot_token",),
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
                    "description": "Array of filter groups as JSON. Each group contains \"filters\" array with objects having \"propertyName\", \"operator\" (e.g., \"EQ\", \"CONTAINS_TOKEN\", \"GT\"), and \"value\"",
                },
                "sorts": {
                    "type": "array",
                    "description": "Array of sort objects as JSON with \"propertyName\" and \"direction\" (\"ASCENDING\" or \"DESCENDING\")",
                },
                "query": {
                    "type": "string",
                    "description": "Search query string to match against company name, domain, and other text fields",
                },
                "properties": {
                    "type": "array",
                    "description": "Array of HubSpot property names to return (e.g., [\"name\", \"domain\", \"industry\"])",
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
        
        body: Dict[str, Any] = {}
        
        # filterGroups
        fg = parameters.get("filterGroups")
        if fg is not None:
            if isinstance(fg, str):
                try:
                    fg = json.loads(fg)
                except json.JSONDecodeError as e:
                    return ToolResult(success=False, output="", error=f"Invalid JSON for filterGroups: {str(e)}")
            if isinstance(fg, list) and len(fg) > 0:
                body["filterGroups"] = fg
        
        # sorts
        sg = parameters.get("sorts")
        if sg is not None:
            if isinstance(sg, str):
                try:
                    sg = json.loads(sg)
                except json.JSONDecodeError as e:
                    return ToolResult(success=False, output="", error=f"Invalid JSON for sorts: {str(e)}")
            if isinstance(sg, list) and len(sg) > 0:
                body["sorts"] = sg
        
        # properties
        props = parameters.get("properties")
        if props is not None:
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except json.JSONDecodeError as e:
                    return ToolResult(success=False, output="", error=f"Invalid JSON for properties: {str(e)}")
            if isinstance(props, list) and len(props) > 0:
                body["properties"] = props
        
        # query
        if parameters.get("query"):
            body["query"] = parameters["query"]
        
        # limit
        limit = parameters.get("limit")
        if limit is not None:
            body["limit"] = limit
        
        # after
        if parameters.get("after"):
            body["after"] = parameters["after"]
        
        url = "https://api.hubapi.com/crm/v3/objects/companies/search"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from urllib.parse import urlencode
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotGetContactTool(BaseTool):
    name = "hubspot_get_contact"
    description = "Retrieve a single contact by ID or email from HubSpot"
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
                "contactId": {
                    "type": "string",
                    "description": "The HubSpot contact ID (numeric string) or email address to retrieve",
                },
                "idProperty": {
                    "type": "string",
                    "description": 'Property to use as unique identifier (e.g., "email"). If not specified, uses record ID',
                },
                "properties": {
                    "type": "string",
                    "description": 'Comma-separated list of HubSpot property names to return (e.g., "email,firstname,lastname,phone")',
                },
                "associations": {
                    "type": "string",
                    "description": 'Comma-separated list of object types to retrieve associated IDs for (e.g., "companies,deals")',
                },
            },
            "required": ["contactId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        contact_id = parameters["contactId"].strip()
        base_url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
        
        query_params: dict = {}
        id_property = parameters.get("idProperty")
        if id_property:
            query_params["idProperty"] = id_property
        
        properties_param = parameters.get("properties")
        if properties_param:
            query_params["properties"] = properties_param
        
        associations_param = parameters.get("associations")
        if associations_param:
            query_params["associations"] = associations_param
        
        query_string = urlencode(query_params) if query_params else ""
        url = f"{base_url}?{query_string}" if query_string else base_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
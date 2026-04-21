from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotUpdateContactTool(BaseTool):
    name = "hubspot_update_contact"
    description = "Update an existing contact in HubSpot by ID or email"
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
                "contactId": {
                    "type": "string",
                    "description": "The HubSpot contact ID (numeric string) or email of the contact to update",
                },
                "idProperty": {
                    "type": "string",
                    "description": 'Property to use as unique identifier (e.g., "email"). If not specified, uses record ID',
                },
                "properties": {
                    "type": "object",
                    "description": 'Contact properties to update as JSON object (e.g., {"firstname": "John", "phone": "+1234567890"})',
                },
            },
            "required": ["contactId", "properties"],
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
        url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
        id_property = parameters.get("idProperty")
        if id_property:
            url += f"?idProperty={id_property}"
        
        body = {
            "properties": parameters["properties"],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
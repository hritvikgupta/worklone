from typing import Any, Dict
import httpx
import json
import urllib.parse
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HubspotUpdateTicketTool(BaseTool):
    name = "hubspot_update_ticket"
    description = "Update an existing ticket in HubSpot by ID"
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
                "ticketId": {
                    "type": "string",
                    "description": "The HubSpot ticket ID to update",
                },
                "idProperty": {
                    "type": "string",
                    "description": "Property to use as unique identifier. If not specified, uses record ID",
                },
                "properties": {
                    "type": "object",
                    "description": 'Ticket properties to update as JSON object (e.g., {"subject": "Updated subject", "hs_ticket_priority": "HIGH"})',
                },
            },
            "required": ["ticketId", "properties"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        ticket_id = (parameters.get("ticketId") or "").strip()
        if not ticket_id:
            return ToolResult(success=False, output="", error="Ticket ID is required.")
        
        url = f"https://api.hubapi.com/crm/v3/objects/tickets/{urllib.parse.quote(ticket_id)}"
        
        id_property = parameters.get("idProperty")
        if id_property:
            url += f"?idProperty={urllib.parse.quote(id_property)}"
        
        properties_raw = parameters.get("properties")
        if properties_raw is None:
            return ToolResult(success=False, output="", error="Properties are required.")
        
        if isinstance(properties_raw, str):
            try:
                properties = json.loads(properties_raw)
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="Invalid JSON format for properties. Please provide a valid JSON object.")
        else:
            properties = properties_raw
        
        body = {"properties": properties}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", "Failed to update ticket in HubSpot")
                    except:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomCreateTicketTool(BaseTool):
    name = "intercom_create_ticket"
    description = "Create a new ticket in Intercom. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INTERCOM_ACCESS_TOKEN",
                description="Intercom API access token",
                env_var="INTERCOM_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "intercom",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticket_type_id": {
                    "type": "string",
                    "description": "The ID of the ticket type",
                },
                "contacts": {
                    "type": "string",
                    "description": "JSON array of contact identifiers (e.g., [{\"id\": \"contact_id\"}])",
                },
                "ticket_attributes": {
                    "type": "string",
                    "description": "JSON object with ticket attributes including _default_title_ and _default_description_",
                },
                "company_id": {
                    "type": "string",
                    "description": "Company ID to associate the ticket with",
                },
                "created_at": {
                    "type": "number",
                    "description": "Unix timestamp for when the ticket was created. If not provided, current time is used.",
                },
                "conversation_to_link_id": {
                    "type": "string",
                    "description": "ID of an existing conversation to link to this ticket",
                },
                "disable_notifications": {
                    "type": "boolean",
                    "description": "When true, suppresses notifications when the ticket is created",
                },
            },
            "required": ["ticket_type_id", "contacts", "ticket_attributes"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        url = "https://api.intercom.io/tickets"
        
        ticket_type_id = parameters["ticket_type_id"]
        
        try:
            contacts_list = json.loads(parameters["contacts"])
        except json.JSONDecodeError:
            contacts_list = [{"id": parameters["contacts"]}]
        
        try:
            ticket_attrs = json.loads(parameters["ticket_attributes"])
        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="ticket_attributes must be a valid JSON object")
        
        ticket = {
            "ticket_type_id": ticket_type_id,
            "contacts": contacts_list,
            "ticket_attributes": ticket_attrs,
        }
        
        for key in ["company_id", "created_at", "conversation_to_link_id", "disable_notifications"]:
            if key in parameters:
                ticket[key] = parameters[key]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=ticket)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
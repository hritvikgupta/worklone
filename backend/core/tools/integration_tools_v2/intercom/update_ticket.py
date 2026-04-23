from typing import Any, Dict
import httpx
import json
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IntercomUpdateTicketTool(BaseTool):
    name = "Update Ticket in Intercom"
    description = "Update a ticket in Intercom (change state, assignment, attributes)"
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
        token = (context or {}).get("INTERCOM_ACCESS_TOKEN")
        if not token:
            token = os.environ.get("INTERCOM_ACCESS_TOKEN")
        if self._is_placeholder_token(token):
            return ""
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticketId": {
                    "type": "string",
                    "description": "The ID of the ticket to update",
                },
                "ticket_attributes": {
                    "type": "string",
                    "description": "JSON object with ticket attributes (e.g., {\"_default_title_\":\"New Title\",\"_default_description_\":\"Updated description\"})",
                },
                "open": {
                    "type": "boolean",
                    "description": "Set to false to close the ticket, true to keep it open",
                },
                "is_shared": {
                    "type": "boolean",
                    "description": "Whether the ticket is visible to users",
                },
                "snoozed_until": {
                    "type": "number",
                    "description": "Unix timestamp for when the ticket should reopen",
                },
                "admin_id": {
                    "type": "string",
                    "description": "The ID of the admin performing the update (needed for workflows and attribution)",
                },
                "assignee_id": {
                    "type": "string",
                    "description": "The ID of the admin or team to assign the ticket to. Set to \"0\" to unassign.",
                },
            },
            "required": ["ticketId"],
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
        
        ticket_id = parameters["ticketId"]
        url = f"https://api.intercom.io/tickets/{ticket_id}"
        
        payload: dict[str, Any] = {}
        ticket_attrs_str = parameters.get("ticket_attributes")
        if ticket_attrs_str:
            try:
                payload["ticket_attributes"] = json.loads(ticket_attrs_str)
            except json.JSONDecodeError:
                return ToolResult(
                    success=False,
                    output="",
                    error="ticket_attributes must be a valid JSON object",
                )
        
        if "open" in parameters:
            payload["open"] = parameters["open"]
        if "is_shared" in parameters:
            payload["is_shared"] = parameters["is_shared"]
        if "snoozed_until" in parameters:
            payload["snoozed_until"] = parameters["snoozed_until"]
        
        admin_id = parameters.get("admin_id")
        if admin_id:
            payload["admin_id"] = admin_id
        
        assignee_id = parameters.get("assignee_id")
        if assignee_id:
            payload["assignee_id"] = assignee_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=payload)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
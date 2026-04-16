from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HubspotGetTicketTool(BaseTool):
    name = "hubspot_get_ticket"
    description = "Retrieve a single ticket by ID from HubSpot"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUBSPOT_ACCESS_TOKEN",
                description="Access token for HubSpot",
                env_var="HUBSPOT_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "hubspot",
            context=context,
            context_token_keys=("provider_token",),
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
                    "description": "The HubSpot ticket ID to retrieve",
                },
                "idProperty": {
                    "type": "string",
                    "description": "Property to use as unique identifier. If not specified, uses record ID",
                },
                "properties": {
                    "type": "string",
                    "description": 'Comma-separated list of HubSpot property names to return (e.g., "subject,content,hs_ticket_priority")',
                },
                "associations": {
                    "type": "string",
                    "description": 'Comma-separated list of object types to retrieve associated IDs for (e.g., "contacts,companies")',
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
        }

        ticket_id = parameters["ticketId"].strip()
        url = f"https://api.hubapi.com/crm/v3/objects/tickets/{ticket_id}"

        query_params: Dict[str, str] = {}
        if parameters.get("idProperty"):
            query_params["idProperty"] = parameters["idProperty"]
        if parameters.get("properties"):
            query_params["properties"] = parameters["properties"]
        if parameters.get("associations"):
            query_params["associations"] = parameters["associations"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
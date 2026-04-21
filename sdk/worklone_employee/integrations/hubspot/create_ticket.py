from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotCreateTicketTool(BaseTool):
    name = "hubspot_create_ticket"
    description = "Create a new ticket in HubSpot. Requires subject and hs_pipeline_stage properties"
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
                "properties": {
                    "type": "object",
                    "description": 'Ticket properties as JSON object. Must include subject and hs_pipeline_stage (e.g., {"subject": "Support request", "hs_pipeline_stage": "1", "hs_ticket_priority": "HIGH"})',
                },
                "associations": {
                    "type": "array",
                    "description": 'Array of associations to create with the ticket as JSON. Each object should have "to.id" and "types" array with "associationCategory" and "associationTypeId"',
                },
            },
            "required": ["properties"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        properties = parameters["properties"]
        if isinstance(properties, str):
            properties = json.loads(properties)
        associations = parameters.get("associations")
        body: dict = {"properties": properties}
        if associations and len(associations) > 0:
            body["associations"] = associations
        
        url = "https://api.hubapi.com/crm/v3/objects/tickets"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text)
                    except:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class HubspotCreateAppointmentTool(BaseTool):
    name = "hubspot_create_appointment"
    description = "Create a new appointment in HubSpot"
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
            context_token_keys=("access_token",),
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
                    "description": 'Appointment properties as JSON object (e.g., {"hs_meeting_title": "Discovery Call", "hs_meeting_start_time": "2024-01-15T10:00:00Z", "hs_meeting_end_time": "2024-01-15T11:00:00Z"})',
                },
                "associations": {
                    "type": "array",
                    "description": 'Array of associations to create with the appointment as JSON. Each object should have "to.id" and "types" array with "associationCategory" and "associationTypeId"',
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
            try:
                properties = json.loads(properties)
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="Invalid JSON format for properties. Please provide a valid JSON object.")
        
        body: Dict[str, Any] = {"properties": properties}
        associations = parameters.get("associations")
        if associations:
            body["associations"] = associations
        
        url = "https://api.hubapi.com/crm/v3/objects/appointments"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
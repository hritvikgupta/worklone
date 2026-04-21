from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class HubspotCreateDealTool(BaseTool):
    name = "hubspot_create_deal"
    description = "Create a new deal in HubSpot. Requires at least a dealname property"
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
                    "description": 'Deal properties as JSON object. Must include dealname (e.g., {"dealname": "New Deal", "amount": "5000", "dealstage": "appointmentscheduled"})',
                },
                "associations": {
                    "type": "array",
                    "description": 'Array of associations to create with the deal as JSON. Each object should have "to.id" and "types" array with "associationCategory" and "associationTypeId"',
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
        
        url = "https://api.hubapi.com/crm/v3/objects/deals"
        
        properties = parameters.get("properties")
        if properties is None:
            return ToolResult(success=False, output="", error="Properties are required.")
        if isinstance(properties, str):
            try:
                properties = json.loads(properties)
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="Invalid JSON format for properties. Please provide a valid JSON object.")
        
        associations = parameters.get("associations")
        body: Dict[str, Any] = {"properties": properties}
        if associations and len(associations) > 0:
            body["associations"] = associations
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", response.text) or "Failed to create deal in HubSpot"
                    except json.JSONDecodeError:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
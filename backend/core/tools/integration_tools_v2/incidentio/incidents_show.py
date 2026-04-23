from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioIncidentsShowTool(BaseTool):
    name = "incidentio_incidents_show"
    description = "Retrieve detailed information about a specific incident from incident.io by its ID. Returns full incident details including custom fields and role assignments."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INCIDENTIO_API_KEY",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": 'ID of the incident to retrieve (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = context.get("INCIDENTIO_API_KEY") if context else None
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        id_ = parameters["id"]
        url = f"https://api.incident.io/v2/incidents/{id_}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
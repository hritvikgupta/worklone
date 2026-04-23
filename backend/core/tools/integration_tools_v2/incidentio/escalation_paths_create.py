from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IncidentioEscalationPathsCreateTool(BaseTool):
    name = "incidentio_escalation_paths_create"
    description = "Create a new escalation path in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="incidentio_api_key",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "incidentio",
            context=context,
            context_token_keys=("incidentio_api_key",),
            env_token_keys=("INCIDENTIO_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": 'Name of the escalation path (e.g., "Critical Incident Path")',
                },
                "path": {
                    "type": "array",
                    "description": 'Array of escalation levels with targets and time to acknowledge in seconds. Each level should have: targets (array of {id, type, schedule_id?, user_id?, urgency}) and time_to_ack_seconds (number)',
                },
                "working_hours": {
                    "type": "array",
                    "description": 'Optional working hours configuration. Array of {weekday, start_time, end_time}',
                },
            },
            "required": ["name", "path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.incident.io/v2/escalation_paths"
        
        body = {
            "name": parameters["name"],
            "path": parameters["path"],
        }
        working_hours = parameters.get("working_hours")
        if working_hours is not None:
            body["working_hours"] = working_hours
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
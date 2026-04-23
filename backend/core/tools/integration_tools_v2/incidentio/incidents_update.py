import httpx
import os
from typing import Any, Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioIncidentsUpdateTool(BaseTool):
    name = "incidentio_incidents_update"
    description = "Update an existing incident in incident.io. Can update name, summary, severity, status, or type."
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("INCIDENTIO_API_KEY") if context else None
        if api_key is None or api_key == "":
            api_key = os.getenv("INCIDENTIO_API_KEY", "")
        return api_key

    def _build_body(self, parameters: dict) -> dict:
        incident: Dict[str, Any] = {}
        for key in ["name", "summary", "severity_id", "incident_status_id", "incident_type_id"]:
            value = parameters.get(key)
            if value:
                incident[key] = value
        return {
            "incident": incident,
            "notify_incident_channel": parameters["notify_incident_channel"],
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": 'ID of the incident to update (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
                "name": {
                    "type": "string",
                    "description": 'Updated name of the incident (e.g., "Database connection issues")',
                },
                "summary": {
                    "type": "string",
                    "description": 'Updated summary of the incident (e.g., "Intermittent connection failures to primary database")',
                },
                "severity_id": {
                    "type": "string",
                    "description": 'Updated severity ID for the incident (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
                "incident_status_id": {
                    "type": "string",
                    "description": 'Updated status ID for the incident (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
                "incident_type_id": {
                    "type": "string",
                    "description": "Updated incident type ID",
                },
                "notify_incident_channel": {
                    "type": "boolean",
                    "description": "Whether to notify the incident channel about this update",
                },
            },
            "required": ["id", "notify_incident_channel"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = f"https://api.incident.io/v2/incidents/{parameters['id']}/actions/edit"
        body = self._build_body(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
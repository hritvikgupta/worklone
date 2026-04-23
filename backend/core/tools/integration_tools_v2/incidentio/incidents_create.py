from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioIncidentsCreateTool(BaseTool):
    name = "incident.io Incidents Create"
    description = "Create a new incident in incident.io. Requires idempotency_key, severity_id, and visibility. Optionally accepts name, summary, type, and status."
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
                "idempotency_key": {
                    "type": "string",
                    "description": "Unique identifier to prevent duplicate incident creation. Use a UUID or unique string.",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the incident (e.g., \"Database connection issues\")",
                },
                "summary": {
                    "type": "string",
                    "description": "Brief summary of the incident (e.g., \"Intermittent connection failures to primary database\")",
                },
                "severity_id": {
                    "type": "string",
                    "description": "ID of the severity level (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
                "incident_type_id": {
                    "type": "string",
                    "description": "ID of the incident type",
                },
                "incident_status_id": {
                    "type": "string",
                    "description": "ID of the initial incident status",
                },
                "visibility": {
                    "type": "string",
                    "description": 'Visibility of the incident: "public" or "private" (required)',
                },
            },
            "required": ["idempotency_key", "severity_id", "visibility"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("INCIDENTIO_API_KEY") if context else None

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        body = {
            "idempotency_key": parameters["idempotency_key"],
            "severity_id": parameters["severity_id"],
            "visibility": parameters["visibility"],
        }
        if parameters.get("name"):
            body["name"] = parameters["name"]
        if parameters.get("summary"):
            body["summary"] = parameters["summary"]
        if parameters.get("incident_type_id"):
            body["incident_type_id"] = parameters["incident_type_id"]
        if parameters.get("incident_status_id"):
            body["incident_status_id"] = parameters["incident_status_id"]

        url = "https://api.incident.io/v2/incidents"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
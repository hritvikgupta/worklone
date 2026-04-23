from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioEscalationPathsUpdateTool(BaseTool):
    name = "incidentio_escalation_paths_update"
    description = "Update an existing escalation path in incident.io"
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
        token_key = "incidentio_api_key"
        token = context.get(token_key) if context else None
        if token is None:
            token = os.getenv("INCIDENTIO_API_KEY")
        if self._is_placeholder_token(token or ""):
            return ""
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The ID of the escalation path to update (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
                "name": {
                    "type": "string",
                    "description": "New name for the escalation path (e.g., \"Critical Incident Path\")",
                },
                "path": {
                    "type": "array",
                    "description": "New escalation path configuration. Array of escalation levels with targets and time_to_ack_seconds",
                },
                "working_hours": {
                    "type": "array",
                    "description": "New working hours configuration. Array of {weekday, start_time, end_time}",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="incident.io API key not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"https://api.incident.io/v2/escalation_paths/{parameters['id']}"

        body: Dict[str, Any] = {}
        for field in ["name", "path", "working_hours"]:
            if field in parameters and parameters[field] is not None:
                body[field] = parameters[field]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
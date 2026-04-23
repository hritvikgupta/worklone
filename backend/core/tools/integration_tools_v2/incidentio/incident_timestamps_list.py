from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioIncidentTimestampsListTool(BaseTool):
    name = "incidentio_incident_timestamps_list"
    description = "List all incident timestamp definitions in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "incident.io API Key",
                },
            },
            "required": ["apiKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey")

        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="incident.io API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        url = "https://api.incident.io/v2/incident_timestamps"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    incident_timestamps = data.get("incident_timestamps") or data
                    output_data = {"incident_timestamps": incident_timestamps}
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
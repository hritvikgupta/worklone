from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioRolesShowTool(BaseTool):
    name = "Show Incident Role"
    description = "Get details of a specific incident role in incident.io"
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
                    "description": 'The ID of the incident role (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("INCIDENTIO_API_KEY") if context else None

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        id_ = parameters["id"]
        url = f"https://api.incident.io/v2/incident_roles/{id_}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    resp_data = response.json()
                    transformed_data = {
                        "incident_role": resp_data.get("incident_role") or resp_data,
                    }
                    return ToolResult(success=True, output=response.text, data=transformed_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
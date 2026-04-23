from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioWorkflowsUpdateTool(BaseTool):
    name = "incidentio_workflows_update"
    description = "Update an existing workflow in incident.io."
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
                    "description": 'The ID of the workflow to update (e.g., "01FCNDV6P870EA6S7TK1DSYDG0")',
                },
                "name": {
                    "type": "string",
                    "description": 'New name for the workflow (e.g., "Notify on Critical Incidents")',
                },
                "state": {
                    "type": "string",
                    "description": "New state for the workflow (active, draft, or disabled)",
                },
                "folder": {
                    "type": "string",
                    "description": "New folder for the workflow",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("INCIDENTIO_API_KEY")
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        id_ = parameters["id"]
        url = f"https://api.incident.io/v2/workflows/{id_}"

        body: dict = {}
        if parameters.get("name"):
            body["name"] = parameters["name"]
        if parameters.get("state"):
            body["state"] = parameters["state"]
        if parameters.get("folder"):
            body["folder"] = parameters["folder"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
import os
import httpx
from typing import Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioWorkflowsDeleteTool(BaseTool):
    name = "incident_io_workflows_delete"
    description = "Delete a workflow in incident.io."
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
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The ID of the workflow to delete (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"https://api.incident.io/v2/workflows/{parameters['id']}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 204]:
                    return ToolResult(
                        success=True,
                        output="Workflow deleted successfully.",
                        data={"message": "Workflow deleted successfully."},
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioIncidentUpdatesListTool(BaseTool):
    name = "incidentio_incident_updates_list"
    description = "List all updates for a specific incident in incident.io"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        token_key = "INCIDENTIO_API_KEY"
        token = context.get(token_key) if context else None
        if token is None:
            token = os.getenv(token_key)
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "The ID of the incident to get updates for (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\"). If not provided, returns all updates",
                },
                "page_size": {
                    "type": "number",
                    "description": "Number of results to return per page (e.g., 10, 25, 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://api.incident.io/v2/incident_updates"
        params_dict: Dict[str, Any] = {k: v for k, v in parameters.items()}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
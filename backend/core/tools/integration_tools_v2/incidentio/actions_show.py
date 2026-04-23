from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class IncidentioActionsShowTool(BaseTool):
    name = "incidentio_actions_show"
    description = "Get detailed information about a specific action from incident.io."
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

    def _resolve_api_key(self, context: dict | None) -> str:
        candidate_keys = ["incidentio_api_key", "api_key", "INCIDENTIO_API_KEY"]
        if context:
            for key in candidate_keys:
                token = context.get(key)
                if token and not self._is_placeholder_token(token):
                    return token
        token = os.getenv("INCIDENTIO_API_KEY")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Action ID (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = f"https://api.incident.io/v2/actions/{parameters['id']}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
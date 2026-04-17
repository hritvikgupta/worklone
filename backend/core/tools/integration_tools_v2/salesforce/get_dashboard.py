from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceGetDashboardTool(BaseTool):
    name = "salesforce_get_dashboard"
    description = "Get details and results for a specific dashboard"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_connection(self, context: dict | None) -> tuple[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        access_token = connection.access_token
        instance_url = getattr(connection, "instance_url", None)
        if not instance_url:
            raise ValueError("Instance URL not available in the OAuth connection.")
        return access_token, instance_url

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "dashboardId": {
                    "type": "string",
                    "description": "Salesforce Dashboard ID (18-character string starting with 01Z)",
                },
            },
            "required": ["dashboardId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            access_token, instance_url = await self._resolve_connection(context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        if self._is_placeholder_token(access_token) or self._is_placeholder_token(instance_url or ""):
            return ToolResult(success=False, output="", error="Salesforce access token or instance URL not configured.")

        dashboard_id = parameters.get("dashboardId")
        if not dashboard_id:
            return ToolResult(success=False, output="", error="Dashboard ID is required.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{instance_url.rstrip('/')}/services/data/v59.0/analytics/dashboards/{dashboard_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
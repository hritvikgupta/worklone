from typing import Any, Dict, Tuple
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceRefreshDashboardTool(BaseTool):
    name = "salesforce_refresh_dashboard"
    description = "Refresh a dashboard to get the latest data"
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

    async def _resolve_connection(self, context: dict | None) -> Tuple[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token, getattr(connection, "instance_url", "")

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
        dashboard_id = (parameters.get("dashboardId") or "").strip()
        if not dashboard_id:
            return ToolResult(success=False, output="", error="Dashboard ID is required. Please provide a valid Salesforce Dashboard ID.")

        access_token, instance_url = await self._resolve_connection(context)

        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Access token or instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"{instance_url.rstrip('/')}/services/data/v59.0/analytics/dashboards/{dashboard_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json={})

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
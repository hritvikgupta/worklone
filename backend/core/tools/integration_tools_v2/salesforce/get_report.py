from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceGetReportTool(BaseTool):
    name = "salesforce_get_report"
    description = "Get metadata and describe information for a specific report"
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

    async def _get_credentials(self, context: dict | None) -> tuple[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        access_token = connection.access_token
        if self._is_placeholder_token(access_token):
            raise ValueError("Access token not configured.")
        instance_url = connection.instance_url
        if not instance_url or not instance_url.startswith("https://"):
            raise ValueError("Instance URL not configured.")
        return access_token, instance_url

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "reportId": {
                    "type": "string",
                    "description": "Salesforce Report ID (18-character string starting with 00O)",
                },
            },
            "required": ["reportId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        report_id = (parameters.get("reportId") or "").strip()
        if not report_id:
            return ToolResult(success=False, output="", error="Report ID is required. Please provide a valid Salesforce Report ID.")

        try:
            access_token, instance_url = await self._get_credentials(context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        url = f"{instance_url.rstrip('/')}/services/data/v59.0/analytics/reports/{report_id}/describe"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200]:
                    data = response.json()
                    output = {
                        "report": data,
                        "reportId": report_id,
                        "success": True,
                    }
                    return ToolResult(success=True, output=output, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
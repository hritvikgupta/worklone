from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SalesforceRunReportTool(BaseTool):
    name = "salesforce_run_report"
    description = "Execute a report and retrieve the results"
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

    async def _resolve_connection(self, context: dict | None) -> Any:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken", "idToken", "instanceUrl"),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "reportId": {
                    "type": "string",
                    "description": "Salesforce Report ID (18-character string starting with 00O)",
                },
                "includeDetails": {
                    "type": "string",
                    "description": "Include detail rows (true/false, default: true)",
                },
                "filters": {
                    "type": "string",
                    "description": "JSON array of report filter objects to apply",
                },
            },
            "required": ["reportId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = connection.instance_url

        if self._is_placeholder_token(access_token) or self._is_placeholder_token(str(instance_url or "")):
            return ToolResult(success=False, output="", error="Access token or instance URL not configured.")

        report_id = parameters.get("reportId")
        if not report_id or report_id.strip() == "":
            return ToolResult(success=False, output="", error="Report ID is required. Please provide a valid Salesforce Report ID.")

        include_details_str = parameters.get("includeDetails", "true")
        include_details = include_details_str != "false"
        filters_str = parameters.get("filters")

        url = f"{instance_url}/services/data/v59.0/analytics/reports/{report_id}?includeDetails={include_details}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        json_body = None
        if filters_str:
            try:
                filters = json.loads(filters_str)
                json_body = {"reportMetadata": {"reportFilters": filters}}
            except json.JSONDecodeError as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid report filters JSON: {str(e)}. Please provide a valid JSON array of filter objects.",
                )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if json_body:
                    response = await client.post(url, headers=headers, json=json_body)
                else:
                    response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
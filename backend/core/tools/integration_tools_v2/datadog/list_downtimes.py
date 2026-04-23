from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogListDowntimesTool(BaseTool):
    name = "datadog_list_downtimes"
    description = "List all scheduled downtimes in Datadog."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Datadog API key",
                env_var="DATADOG_API_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="applicationKey",
                description="Datadog Application key",
                env_var="DATADOG_APPLICATION_KEY",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "currentOnly": {
                    "type": "boolean",
                    "description": "Only return currently active downtimes",
                },
                "monitorId": {
                    "type": "string",
                    "description": 'Filter by monitor ID (e.g., "12345678")',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") if context else None
        application_key = context.get("applicationKey") if context else None
        site = context.get("site", "datadoghq.com") if context else "datadoghq.com"

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(application_key):
            return ToolResult(success=False, output="", error="Datadog API key or application key not configured.")

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": application_key,
        }

        url = f"https://api.{site}/api/v2/downtime"
        query_params: Dict[str, str] = {}
        current_only = parameters.get("currentOnly")
        if current_only:
            query_params["current_only"] = "true"
        monitor_id = parameters.get("monitorId")
        if monitor_id:
            query_params["monitor_id"] = monitor_id

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
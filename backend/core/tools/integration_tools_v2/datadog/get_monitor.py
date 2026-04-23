from typing import Any, Dict
import httpx
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogGetMonitorTool(BaseTool):
    name = "datadog_get_monitor"
    description = "Retrieve details of a specific monitor by ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="datadog_api_key",
                description="Datadog API key",
                env_var="DATADOG_API_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="datadog_application_key",
                description="Datadog Application key",
                env_var="DATADOG_APPLICATION_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="site",
                description="Datadog site/region (default: datadoghq.com)",
                env_var="DATADOG_SITE",
                required=False,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "monitorId": {
                    "type": "string",
                    "description": "The ID of the monitor to retrieve (e.g., \"12345678\")",
                },
                "groupStates": {
                    "type": "string",
                    "description": "Comma-separated group states to include (e.g., \"alert,warn\", \"alert,warn,no data,ok\")",
                },
                "withDowntimes": {
                    "type": "boolean",
                    "description": "Include downtime data with the monitor",
                },
            },
            "required": ["monitorId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = context.get("datadog_api_key") if context else None
        app_key = context.get("datadog_application_key") if context else None
        site = context.get("site", "datadoghq.com") if context else "datadoghq.com"

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(app_key):
            return ToolResult(success=False, output="", error="Datadog API key or Application key not configured.")

        monitor_id = parameters["monitorId"]
        group_states = parameters.get("groupStates")
        with_downtimes = parameters.get("withDowntimes", False)

        query_params: dict[str, str] = {}
        if group_states:
            query_params["group_states"] = group_states
        if with_downtimes:
            query_params["with_downtimes"] = "true"

        url = f"https://api.{site}/api/v1/monitor/{monitor_id}"
        query_string = urlencode(query_params)
        if query_string:
            url += f"?{query_string}"

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict) and "errors" in error_data and error_data["errors"]:
                            error_msg = error_data["errors"][0]
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogListMonitorsTool(BaseTool):
    name = "Datadog List Monitors"
    description = "List all monitors in Datadog with optional filtering by name, tags, or state."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DATADOG_API_KEY",
                description="Datadog API key",
                env_var="DATADOG_API_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="DATADOG_APPLICATION_KEY",
                description="Datadog Application key",
                env_var="DATADOG_APPLICATION_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="DATADOG_SITE",
                description="Datadog site/region (default: datadoghq.com)",
                env_var="DATADOG_SITE",
                required=False,
                auth_type="api_key",
            ),
        ]

    def _build_params(self, parameters: dict) -> dict:
        params = {}
        if group_states := parameters.get("groupStates"):
            params["group_states"] = group_states
        if name := parameters.get("name"):
            params["name"] = name
        if tags := parameters.get("tags"):
            params["tags"] = tags
        if monitor_tags := parameters.get("monitorTags"):
            params["monitor_tags"] = monitor_tags
        if with_downtimes := parameters.get("withDowntimes"):
            params["with_downtimes"] = "true"
        if page := parameters.get("page"):
            params["page"] = page
        if page_size := parameters.get("pageSize"):
            params["page_size"] = page_size
        return params

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "groupStates": {
                    "type": "string",
                    "description": 'Comma-separated group states to filter by (e.g., "alert,warn", "alert,warn,no data,ok")',
                },
                "name": {
                    "type": "string",
                    "description": 'Filter monitors by name with partial match (e.g., "CPU", "Production")',
                },
                "tags": {
                    "type": "string",
                    "description": 'Comma-separated list of tags to filter by (e.g., "env:prod,team:backend")',
                },
                "monitorTags": {
                    "type": "string",
                    "description": 'Comma-separated list of monitor tags to filter by (e.g., "service:api,priority:high")',
                },
                "withDowntimes": {
                    "type": "boolean",
                    "description": "Include downtime data with monitors",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (0-indexed, e.g., 0, 1, 2)",
                },
                "pageSize": {
                    "type": "number",
                    "description": "Number of monitors per page (e.g., 50, max: 1000)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("DATADOG_API_KEY") if context else None
        application_key = context.get("DATADOG_APPLICATION_KEY") if context else None
        site = context.get("DATADOG_SITE", "datadoghq.com") if context else "datadoghq.com"

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(application_key):
            return ToolResult(success=False, output="", error="Datadog API and Application keys not configured.")

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": application_key,
        }

        base_url = f"https://api.{site}/api/v1/monitor"
        query_params = self._build_params(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
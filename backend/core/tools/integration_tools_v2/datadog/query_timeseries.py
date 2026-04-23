from typing import Any, Dict, List
import httpx
import json
import os
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogQueryTimeseriesTool(BaseTool):
    name = "datadog_query_timeseries"
    description = "Query metric timeseries data from Datadog. Use for analyzing trends, creating reports, or retrieving metric values."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
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
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": 'Datadog metrics query (e.g., "avg:system.cpu.user{*}", "sum:nginx.requests{env:prod}.as_count()")',
                },
                "from": {
                    "type": "number",
                    "description": "Start time as Unix timestamp in seconds (e.g., 1705320000)",
                },
                "to": {
                    "type": "number",
                    "description": "End time as Unix timestamp in seconds (e.g., 1705323600)",
                },
                "site": {
                    "type": "string",
                    "description": "Datadog site/region (default: datadoghq.com)",
                },
            },
            "required": ["query", "from", "to"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("datadog_api_key") if context else None
        if self._is_placeholder_token(api_key or ""):
            api_key = os.environ.get("DATADOG_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Datadog API key not configured.")

        app_key = context.get("datadog_application_key") if context else None
        if self._is_placeholder_token(app_key or ""):
            app_key = os.environ.get("DATADOG_APPLICATION_KEY")
        if self._is_placeholder_token(app_key or ""):
            return ToolResult(success=False, output="", error="Datadog Application key not configured.")

        site = parameters.get("site", "datadoghq.com")
        query_params = {
            "query": parameters["query"],
            "from": str(parameters["from"]),
            "to": str(parameters["to"]),
        }
        query_string = urlencode(query_params)
        url = f"https://api.{site}/api/v1/query?{query_string}"

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

            if response.is_success:
                data = response.json()
                series = []
                for s in data.get("series", []):
                    metric = s.get("metric") or s.get("expression")
                    tags = s.get("tag_set", [])
                    points = [
                        {
                            "timestamp": point[0] / 1000,
                            "value": point[1],
                        }
                        for point in s.get("pointlist", [])
                    ]
                    series.append({
                        "metric": metric,
                        "tags": tags,
                        "points": points,
                    })
                result = {
                    "series": series,
                    "status": data.get("status", "ok"),
                }
                return ToolResult(success=True, output=json.dumps(result), data=result)
            else:
                try:
                    error_data = response.json()
                except:
                    error_data = {}
                errors = error_data.get("errors", [])
                error_msg = errors[0] if errors else f"HTTP {response.status_code}: {response.reason_phrase}"
                return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogSubmitMetricsTool(BaseTool):
    name = "datadog_submit_metrics"
    description = "Submit custom metrics to Datadog. Use for tracking application performance, business metrics, or custom monitoring data."
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
                key="DATADOG_SITE",
                description="Datadog site/region (default: datadoghq.com)",
                env_var="DATADOG_SITE",
                required=False,
                auth_type="api_key",
            ),
        ]

    def _get_api_key(self, context: dict | None) -> str | None:
        value = context.get("DATADOG_API_KEY") if context else None
        if self._is_placeholder_token(value or ""):
            return None
        return value

    def _get_site(self, context: dict | None) -> str:
        return (context.get("DATADOG_SITE") if context else None) or "datadoghq.com"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "series": {
                    "type": "string",
                    "description": "JSON array of metric series to submit. Each series should include metric name, type (gauge/rate/count), points (timestamp/value pairs), and optional tags.",
                },
            },
            "required": ["series"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)
        if not api_key:
            return ToolResult(success=False, output="", error="Datadog API key not configured.")

        site = self._get_site(context)

        try:
            series_list = json.loads(parameters["series"])
        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="Invalid JSON in series parameter")

        type_map = {"gauge": 0, "rate": 1, "count": 2}
        formatted_series = []
        for s in series_list:
            metric_type = type_map.get(s.get("type", ""), 3)
            points = [
                {
                    "timestamp": p["timestamp"],
                    "value": p["value"],
                }
                for p in s.get("points", [])
            ]
            formatted = {
                "metric": s["metric"],
                "type": metric_type,
                "points": points,
                "tags": s.get("tags", []),
                "unit": s.get("unit"),
                "resources": s.get("resources", [{"name": "host", "type": "host"}]),
            }
            formatted_series.append(formatted)

        url = f"https://api.{site}/api/v2/series"
        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
        }
        json_body = {"series": formatted_series}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code in [200, 201, 202, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
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
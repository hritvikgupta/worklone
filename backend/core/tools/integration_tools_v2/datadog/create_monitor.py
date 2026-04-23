from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogCreateMonitorTool(BaseTool):
    name = "datadog_create_monitor"
    description = "Create a new monitor/alert in Datadog. Monitors can track metrics, service checks, events, and more."
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
                "name": {
                    "type": "string",
                    "description": "Monitor name",
                },
                "type": {
                    "type": "string",
                    "description": "Monitor type: metric alert, service check, event alert, process alert, log alert, query alert, composite, synthetics alert, slo alert",
                },
                "query": {
                    "type": "string",
                    "description": "Monitor query (e.g., \"avg(last_5m):avg:system.cpu.idle{*} < 20\", \"logs(\\\"status:error\\\").index(\\\"main\\\").rollup(\\\"count\\\").last(\\\"5m\\\") > 100\")",
                },
                "message": {
                    "type": "string",
                    "description": "Message to include with notifications. Can include @-mentions and markdown.",
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated list of tags",
                },
                "priority": {
                    "type": "number",
                    "description": "Monitor priority (1-5, where 1 is highest)",
                },
                "options": {
                    "type": "string",
                    "description": "JSON string of monitor options (thresholds, notify_no_data, renotify_interval, etc.)",
                },
            },
            "required": ["name", "type", "query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") if context else None
        application_key = context.get("applicationKey") if context else None
        site = parameters.get("site", "datadoghq.com")

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Datadog API key not configured.")
        if self._is_placeholder_token(application_key or ""):
            return ToolResult(success=False, output="", error="Datadog Application key not configured.")

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": application_key,
        }

        url = f"https://api.{site}/api/v1/monitor"

        body = {
            "name": parameters["name"],
            "type": parameters["type"],
            "query": parameters["query"],
        }

        message = parameters.get("message")
        if message:
            body["message"] = message

        priority = parameters.get("priority")
        if priority is not None:
            body["priority"] = priority

        tags_str = parameters.get("tags")
        if tags_str:
            body["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

        options_str = parameters.get("options")
        if options_str:
            try:
                body["options"] = json.loads(options_str)
            except json.JSONDecodeError:
                pass

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors", [])
                        error_msg = errors[0] if errors else f"HTTP {response.status_code}: {response.reason_phrase}"
                    except:
                        error_msg = f"HTTP {response.status_code}: {response.reason_phrase}"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
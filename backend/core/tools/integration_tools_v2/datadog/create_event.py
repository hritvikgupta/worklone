from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogCreateEventTool(BaseTool):
    name = "Datadog Create Event"
    description = "Post an event to the Datadog event stream. Use for deployment notifications, alerts, or any significant occurrences."
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Event title",
                },
                "text": {
                    "type": "string",
                    "description": "Event body/description. Supports markdown.",
                },
                "alertType": {
                    "type": "string",
                    "description": "Alert type: error, warning, info, success, user_update, recommendation, or snapshot",
                },
                "priority": {
                    "type": "string",
                    "description": "Event priority: normal or low",
                },
                "host": {
                    "type": "string",
                    "description": "Host name to associate with this event (e.g., \"web-server-01\", \"prod-api-1\")",
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated list of tags (e.g., \"env:production,service:api\", \"team:backend,priority:high\")",
                },
                "aggregationKey": {
                    "type": "string",
                    "description": "Key to aggregate events together",
                },
                "sourceTypeName": {
                    "type": "string",
                    "description": "Source type name for the event",
                },
                "dateHappened": {
                    "type": "number",
                    "description": "Unix timestamp in seconds when the event occurred (e.g., 1705320000, defaults to now)",
                },
            },
            "required": ["title", "text"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("DATADOG_API_KEY") if context else None
        site = context.get("DATADOG_SITE", "datadoghq.com") if context else "datadoghq.com"

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Datadog API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
        }

        body = {
            "title": parameters["title"],
            "text": parameters["text"],
        }

        alert_type = parameters.get("alertType")
        if alert_type:
            body["alert_type"] = alert_type

        priority = parameters.get("priority")
        if priority:
            body["priority"] = priority

        host = parameters.get("host")
        if host:
            body["host"] = host

        tags_str = parameters.get("tags")
        if tags_str:
            body["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

        aggregation_key = parameters.get("aggregationKey")
        if aggregation_key:
            body["aggregation_key"] = aggregation_key

        source_type_name = parameters.get("sourceTypeName")
        if source_type_name:
            body["source_type_name"] = source_type_name

        date_happened = parameters.get("dateHappened")
        if date_happened:
            body["date_happened"] = date_happened

        url = f"https://api.{site}/api/v1/events"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        return ToolResult(success=True, output=response.text, data=data)
                    except Exception:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    try:
                        err_data = response.json()
                        error = err_data.get("errors", [None])[0]
                        if not error:
                            error = response.text or f"HTTP {response.status_code}: {response.reason_phrase}"
                    except Exception:
                        error = response.text or f"HTTP {response.status_code}: {response.reason_phrase}"
                    return ToolResult(success=False, output="", error=error)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
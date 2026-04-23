from typing import Any, Dict
import httpx
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogCreateDowntimeTool(BaseTool):
    name = "datadog_create_downtime"
    description = "Schedule a downtime to suppress monitor notifications during maintenance windows."
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
                "scope": {
                    "type": "string",
                    "description": "Scope to apply downtime to (e.g., \"host:myhost\", \"env:production\", or \"*\" for all)",
                },
                "message": {
                    "type": "string",
                    "description": "Message to display during downtime",
                },
                "start": {
                    "type": "number",
                    "description": "Unix timestamp for downtime start in seconds (e.g., 1705320000, defaults to now)",
                },
                "end": {
                    "type": "number",
                    "description": "Unix timestamp for downtime end in seconds (e.g., 1705323600)",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for the downtime (e.g., \"America/New_York\", \"UTC\", \"Europe/London\")",
                },
                "monitorId": {
                    "type": "string",
                    "description": "Specific monitor ID to mute (e.g., \"12345678\")",
                },
                "monitorTags": {
                    "type": "string",
                    "description": "Comma-separated monitor tags to match (e.g., \"team:backend,priority:high\")",
                },
            },
            "required": ["scope"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") if context else None
        app_key = context.get("applicationKey") if context else None
        site = context.get("site", "datadoghq.com") if context else "datadoghq.com"

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(app_key):
            return ToolResult(success=False, output="", error="Datadog API key and Application key not configured.")

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }

        url = f"https://api.{site}/api/v2/downtime"

        attributes: dict = {"scope": parameters["scope"]}

        schedule: dict = {}
        start = parameters.get("start")
        if start is not None:
            schedule["start"] = datetime.fromtimestamp(start).isoformat()
        end_ts = parameters.get("end")
        if end_ts is not None:
            schedule["end"] = datetime.fromtimestamp(end_ts).isoformat()
        timezone = parameters.get("timezone")
        if timezone:
            schedule["timezone"] = timezone
        if schedule:
            attributes["schedule"] = schedule

        message = parameters.get("message")
        if message:
            attributes["message"] = message

        mute_first = parameters.get("muteFirstRecoveryNotification")
        if mute_first is not None:
            attributes["mute_first_recovery_notification"] = mute_first

        monitor_id = parameters.get("monitorId")
        monitor_tags = parameters.get("monitorTags")
        if monitor_id:
            attributes["monitor_identifier"] = {"monitor_id": int(monitor_id)}
        elif monitor_tags:
            tags = [t.strip() for t in monitor_tags.split(",") if t.strip()]
            attributes["monitor_identifier"] = {"monitor_tags": tags}

        body = {
            "data": {
                "type": "downtime",
                "attributes": attributes,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
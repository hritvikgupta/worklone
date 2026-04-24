from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogMuteMonitorTool(BaseTool):
    name = "datadog_mute_monitor"
    description = "Mute a monitor to temporarily suppress notifications."
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "monitorId": {
                    "type": "string",
                    "description": "The ID of the monitor to mute (e.g., \"12345678\")",
                },
                "scope": {
                    "type": "string",
                    "description": "Scope to mute (e.g., \"host:myhost\", \"env:prod\"). If not specified, mutes all scopes.",
                },
                "end": {
                    "type": "integer",
                    "description": "Unix timestamp in seconds when the mute should end (e.g., 1705323600). If not specified, mutes indefinitely.",
                },
            },
            "required": ["monitorId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("DATADOG_API_KEY") if context else None
        application_key = context.get("DATADOG_APPLICATION_KEY") if context else None
        site = context.get("DATADOG_SITE", "datadoghq.com") if context else "datadoghq.com"

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(application_key):
            return ToolResult(success=False, output="", error="Datadog API key or Application key not configured.")

        monitor_id = parameters.get("monitorId")
        scope = parameters.get("scope")
        end = parameters.get("end")

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": application_key,
        }

        url = f"https://api.{site}/api/v1/monitor/{monitor_id}/mute"

        body = {}
        if scope:
            body["scope"] = scope
        if end is not None:
            body["end"] = end

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
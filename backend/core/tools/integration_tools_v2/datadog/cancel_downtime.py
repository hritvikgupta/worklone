from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogCancelDowntimeTool(BaseTool):
    name = "datadog_cancel_downtime"
    description = "Cancel a scheduled downtime."
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
                "downtimeId": {
                    "type": "string",
                    "description": 'The ID of the downtime to cancel (e.g., "abc123def456")',
                },
            },
            "required": ["downtimeId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") if context else None
        app_key = context.get("applicationKey") if context else None
        site = context.get("site", "datadoghq.com") if context else "datadoghq.com"
        downtime_id = parameters.get("downtimeId")

        if not downtime_id:
            return ToolResult(success=False, output="", error="Missing downtimeId parameter.")

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(app_key):
            return ToolResult(success=False, output="", error="Datadog API key or Application key not configured.")

        url = f"https://api.{site}/api/v2/downtime/{downtime_id}"

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    if response.status_code == 204:
                        return ToolResult(success=True, output='{"success": true}', data={"success": True})
                    else:
                        data = response.json()
                        return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors", [])
                        error_detail = errors[0].get("detail") if errors else None
                        error_msg = error_detail or f"HTTP {response.status_code}: {response.reason_phrase}"
                    except Exception:
                        error_msg = f"HTTP {response.status_code}: {response.reason_phrase}"
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
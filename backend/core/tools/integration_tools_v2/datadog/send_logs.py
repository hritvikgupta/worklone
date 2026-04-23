from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogSendLogsTool(BaseTool):
    name = "datadog_send_logs"
    description = "Send log entries to Datadog for centralized logging and analysis."
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
                "logs": {
                    "type": "string",
                    "description": "JSON array of log entries. Each entry should have message and optionally ddsource, ddtags, hostname, service.",
                },
            },
            "required": ["logs"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("datadog_api_key") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Datadog API key not configured.")

        site = context.get("datadog_site") if context else "datadoghq.com"
        if site == "datadoghq.com":
            logs_host = "http-intake.logs.datadoghq.com"
        elif site == "datadoghq.eu":
            logs_host = "http-intake.logs.datadoghq.eu"
        else:
            logs_host = f"http-intake.logs.{site}"
        url = f"https://{logs_host}/api/v2/logs"

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
        }

        try:
            logs_str = parameters["logs"]
            logs = json.loads(logs_str)
            body = [
                {
                    "ddsource": log.get("ddsource", "custom"),
                    "ddtags": log.get("ddtags", ""),
                    "hostname": log.get("hostname", ""),
                    "message": log["message"],
                    "service": log.get("service", ""),
                }
                for log in logs
            ]

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 202, 204]:
                    return ToolResult(success=True, output='{"success": true}', data={"success": True})
                else:
                    error_msg = f"HTTP {response.status_code}: {response.reason_phrase}"
                    try:
                        error_data = response.json()
                        errors = error_data.get("errors")
                        if errors:
                            error_msg = errors[0]
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="Invalid JSON in logs parameter")
        except KeyError as e:
            return ToolResult(success=False, output="", error=f"Missing required field in log entry: {e}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DatadogQueryLogsTool(BaseTool):
    name = "datadog_query_logs"
    description = "Search and retrieve logs from Datadog. Use for troubleshooting, analysis, or monitoring."
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
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": 'Log search query using Datadog query syntax (e.g., "service:web-app status:error", "host:prod-* @http.status_code:500")',
                },
                "from": {
                    "type": "string",
                    "description": 'Start time in ISO-8601 format or relative time (e.g., "now-1h", "now-15m", "2024-01-15T10:00:00Z")',
                },
                "to": {
                    "type": "string",
                    "description": 'End time in ISO-8601 format or relative time (e.g., "now", "now-5m", "2024-01-15T12:00:00Z")',
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of logs to return (e.g., 50, 100, max: 1000)",
                },
                "sort": {
                    "type": "string",
                    "description": 'Sort order: "timestamp" for oldest first, "-timestamp" for newest first',
                },
                "indexes": {
                    "type": "string",
                    "description": "Comma-separated list of log indexes to search",
                },
                "site": {
                    "type": "string",
                    "description": "Datadog site/region (default: datadoghq.com)",
                },
            },
            "required": ["query", "from", "to"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        credentials = context.get("credentials", {}) if context else {}
        api_key = credentials.get("datadog_api_key")
        application_key = credentials.get("datadog_application_key")

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(application_key):
            return ToolResult(success=False, output="", error="Datadog API key or Application key not configured.")

        site = parameters.get("site", "datadoghq.com")
        url = f"https://api.{site}/api/v2/logs/events/search"

        body: Dict[str, Any] = {
            "filter": {
                "query": parameters["query"],
                "from": parameters["from"],
                "to": parameters["to"],
            },
            "page": {
                "limit": parameters.get("limit", 50),
            },
        }

        sort = parameters.get("sort")
        if sort:
            body["sort"] = sort

        indexes_str = parameters.get("indexes")
        if indexes_str:
            indexes_list = [i.strip() for i in indexes_str.split(",") if i.strip()]
            body["filter"]["indexes"] = indexes_list

        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": application_key,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                    except:
                        error_data = {}
                    error_msg = (
                        error_data.get("errors", [{}])[0].get("detail")
                        if isinstance(error_data.get("errors"), list) and len(error_data["errors"]) > 0
                        else response.text or f"HTTP {response.status_code}: {response.reason_phrase}"
                    )
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
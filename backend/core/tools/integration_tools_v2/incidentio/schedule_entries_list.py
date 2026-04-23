from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class IncidentioScheduleEntriesListTool(BaseTool):
    name = "incidentio_schedule_entries_list"
    description = "List all entries for a specific schedule in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INCIDENTIO_API_KEY",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "incidentio",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("INCIDENTIO_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def _build_url(self, parameters: Dict[str, Any]) -> str:
        base_url = "https://api.incident.io/v2/schedule_entries"
        query_params = {
            "schedule_id": parameters["schedule_id"],
        }
        for param in ["entry_window_start", "entry_window_end", "page_size", "after"]:
            if param in parameters:
                query_params[param] = parameters[param]
        query_string = urllib.parse.urlencode(query_params)
        return f"{base_url}?{query_string}"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "string",
                    "description": "The ID of the schedule to get entries for (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
                "entry_window_start": {
                    "type": "string",
                    "description": "Start date/time to filter entries in ISO 8601 format (e.g., \"2024-01-15T09:00:00Z\")",
                },
                "entry_window_end": {
                    "type": "string",
                    "description": "End date/time to filter entries in ISO 8601 format (e.g., \"2024-01-22T09:00:00Z\")",
                },
                "page_size": {
                    "type": "number",
                    "description": "Number of results to return per page (e.g., 10, 25, 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Cursor for pagination (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
            },
            "required": ["schedule_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = self._build_url(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
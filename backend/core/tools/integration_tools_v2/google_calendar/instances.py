from typing import Any, Dict
import httpx
from urllib.parse import quote, urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleCalendarInstancesTool(BaseTool):
    name = "google_calendar_instances"
    description = "Get instances of a recurring event from Google Calendar. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_CALENDAR_ACCESS_TOKEN",
                description="Access token for Google Calendar API",
                env_var="GOOGLE_CALENDAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-calendar",
            context=context,
            context_token_keys=("google_calendar_token",),
            env_token_keys=("GOOGLE_CALENDAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "calendarId": {
                    "type": "string",
                    "description": "Google Calendar ID (e.g., primary or calendar@group.calendar.google.com)",
                },
                "eventId": {
                    "type": "string",
                    "description": "Recurring event ID to get instances of",
                },
                "timeMin": {
                    "type": "string",
                    "description": "Lower bound for instances (RFC3339 timestamp, e.g., 2025-06-03T00:00:00Z)",
                },
                "timeMax": {
                    "type": "string",
                    "description": "Upper bound for instances (RFC3339 timestamp, e.g., 2025-06-04T00:00:00Z)",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of instances to return (default 250, max 2500)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Token for retrieving subsequent pages of results",
                },
                "showDeleted": {
                    "type": "boolean",
                    "description": "Include deleted instances",
                },
            },
            "required": ["eventId"],
        }

    def _build_url(self, parameters: dict) -> str:
        calendar_id = parameters.get("calendarId", "primary")
        event_id = parameters["eventId"]
        query_params: dict[str, str] = {}
        time_min = parameters.get("timeMin")
        if time_min:
            query_params["timeMin"] = time_min
        time_max = parameters.get("timeMax")
        if time_max:
            query_params["timeMax"] = time_max
        max_results = parameters.get("maxResults")
        if max_results is not None:
            query_params["maxResults"] = str(max_results)
        page_token = parameters.get("pageToken")
        if page_token:
            query_params["pageToken"] = page_token
        show_deleted = parameters.get("showDeleted")
        if show_deleted is not None:
            query_params["showDeleted"] = str(show_deleted).lower()
        base_url = "https://www.googleapis.com/calendar/v3"
        path = f"/calendars/{quote(calendar_id)}/events/{quote(event_id)}/instances"
        url = base_url + path
        if query_params:
            url += "?" + urlencode(query_params)
        return url

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
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
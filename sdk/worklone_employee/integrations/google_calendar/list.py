from typing import Any, Dict
import httpx
import urllib.parse
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleCalendarListTool(BaseTool):
    name = "google_calendar_list"
    description = "List events from Google Calendar. Returns API-aligned fields only."
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
            context_token_keys=("accessToken",),
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
                "timeMin": {
                    "type": "string",
                    "description": "Lower bound for events (RFC3339 timestamp, e.g., 2025-06-03T00:00:00Z)",
                },
                "timeMax": {
                    "type": "string",
                    "description": "Upper bound for events (RFC3339 timestamp, e.g., 2025-06-04T00:00:00Z)",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Order of events returned (startTime or updated)",
                },
                "showDeleted": {
                    "type": "boolean",
                    "description": "Include deleted events",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        calendar_id = parameters.get("calendarId", "primary")
        url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events"
        
        params_dict: Dict[str, str] = {
            "singleEvents": "true",
        }
        time_min = parameters.get("timeMin")
        if time_min:
            params_dict["timeMin"] = time_min
        time_max = parameters.get("timeMax")
        if time_max:
            params_dict["timeMax"] = time_max
        order_by = parameters.get("orderBy")
        if order_by:
            params_dict["orderBy"] = order_by
        show_deleted = parameters.get("showDeleted")
        if show_deleted is not None:
            params_dict["showDeleted"] = str(show_deleted)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
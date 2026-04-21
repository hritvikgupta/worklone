from typing import Any, Dict
import httpx
from urllib.parse import quote, urlencode
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GoogleCalendarUpdateTool(BaseTool):
    name = "google_calendar_update"
    description = "Update an existing event in Google Calendar. Returns API-aligned fields only."
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
                "eventId": {
                    "type": "string",
                    "description": "Google Calendar event ID to update",
                },
                "summary": {
                    "type": "string",
                    "description": "New event title/summary",
                },
                "description": {
                    "type": "string",
                    "description": "New event description",
                },
                "location": {
                    "type": "string",
                    "description": "New event location",
                },
                "startDateTime": {
                    "type": "string",
                    "description": "New start date and time. MUST include timezone offset (e.g., 2025-06-03T10:00:00-08:00) OR provide timeZone parameter",
                },
                "endDateTime": {
                    "type": "string",
                    "description": "New end date and time. MUST include timezone offset (e.g., 2025-06-03T11:00:00-08:00) OR provide timeZone parameter",
                },
                "timeZone": {
                    "type": "string",
                    "description": "Time zone (e.g., America/Los_Angeles). Required if datetime does not include offset.",
                },
                "attendees": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Array of attendee email addresses (replaces existing attendees)",
                },
                "sendUpdates": {
                    "type": "string",
                    "description": "How to send updates to attendees: all, externalOnly, or none",
                },
            },
            "required": ["eventId"],
        }

    def _build_body(self, parameters: dict[str, Any]) -> dict[str, Any]:
        update_data: dict[str, Any] = {}
        for field in ["summary", "description", "location"]:
            value = parameters.get(field)
            if value is not None:
                update_data[field] = value

        start_date_time = parameters.get("startDateTime")
        if start_date_time is not None:
            needs_timezone = "+" not in start_date_time and start_date_time.find("-", 10) == -1
            start: dict[str, Any] = {"dateTime": start_date_time}
            time_zone = parameters.get("timeZone")
            if needs_timezone and time_zone:
                start["timeZone"] = time_zone
            update_data["start"] = start

        end_date_time = parameters.get("endDateTime")
        if end_date_time is not None:
            needs_timezone = "+" not in end_date_time and end_date_time.find("-", 10) == -1
            end: dict[str, Any] = {"dateTime": end_date_time}
            time_zone = parameters.get("timeZone")
            if needs_timezone and time_zone:
                end["timeZone"] = time_zone
            update_data["end"] = end

        attendees_input = parameters.get("attendees")
        if attendees_input is not None:
            attendee_list: list[str] = []
            if isinstance(attendees_input, list):
                attendee_list = [email.strip() for email in attendees_input if isinstance(email, str) and email.strip()]
            elif isinstance(attendees_input, str) and attendees_input.strip():
                attendee_list = [email.strip() for email in attendees_input.split(",") if email.strip()]
            if attendee_list:
                update_data["attendees"] = [{"email": email} for email in attendee_list]
        return update_data

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        base_url = "https://www.googleapis.com/calendar/v3"
        calendar_id = parameters.get("calendarId", "primary")
        event_id = parameters["eventId"]
        query_params: dict[str, str | None] = {}
        send_updates = parameters.get("sendUpdates")
        if send_updates is not None:
            query_params["sendUpdates"] = send_updates
        query_string = urlencode(query_params) if query_params else ""
        url = f"{base_url}/calendars/{quote(calendar_id)}/events/{quote(event_id)}{'?' + query_string if query_string else ''}"

        body = self._build_body(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
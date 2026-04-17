from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleCalendarFreebusyTool(BaseTool):
    name = "google_calendar_freebusy"
    description = "Query free/busy information for one or more Google Calendars. Returns API-aligned fields only."
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
            context_token_keys=("access_token",),
            env_token_keys=("GOOGLE_CALENDAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "calendarIds": {
                    "type": "string",
                    "description": "Comma-separated calendar IDs to query (e.g., \"primary,other@example.com\")",
                },
                "timeMin": {
                    "type": "string",
                    "description": "Start of the time range (RFC3339 timestamp, e.g., 2025-06-03T00:00:00Z)",
                },
                "timeMax": {
                    "type": "string",
                    "description": "End of the time range (RFC3339 timestamp, e.g., 2025-06-04T00:00:00Z)",
                },
                "timeZone": {
                    "type": "string",
                    "description": "IANA time zone (e.g., \"UTC\", \"America/New_York\"). Defaults to UTC.",
                },
            },
            "required": ["calendarIds", "timeMin", "timeMax"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        calendar_ids = [cid.strip() for cid in parameters["calendarIds"].split(",") if cid.strip()]
        body = {
            "timeMin": parameters["timeMin"],
            "timeMax": parameters["timeMax"],
            "timeZone": parameters.get("timeZone", "UTC"),
            "items": [{"id": cid} for cid in calendar_ids],
        }
        url = "https://www.googleapis.com/calendar/v3/freebusy"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
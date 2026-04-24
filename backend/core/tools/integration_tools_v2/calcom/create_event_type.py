from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class CalcomCreateEventTypeTool(BaseTool):
    name = "cal_com_create_event_type"
    description = "Create a new event type in Cal.com"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CALCOM_ACCESS_TOKEN",
                description="Cal.com OAuth access token",
                env_var="CALCOM_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "calcom",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("CALCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the event type",
                },
                "slug": {
                    "type": "string",
                    "description": "Unique slug for the event type URL",
                },
                "lengthInMinutes": {
                    "type": "number",
                    "description": "Duration of the event in minutes",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the event type",
                },
                "slotInterval": {
                    "type": "number",
                    "description": "Interval between available booking slots in minutes",
                },
                "minimumBookingNotice": {
                    "type": "number",
                    "description": "Minimum notice required before booking in minutes",
                },
                "beforeEventBuffer": {
                    "type": "number",
                    "description": "Buffer time before the event in minutes",
                },
                "afterEventBuffer": {
                    "type": "number",
                    "description": "Buffer time after the event in minutes",
                },
                "scheduleId": {
                    "type": "number",
                    "description": "ID of the schedule to use for availability",
                },
                "disableGuests": {
                    "type": "boolean",
                    "description": "Whether to disable guests from being added to bookings",
                },
            },
            "required": ["title", "slug", "lengthInMinutes"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "cal-api-version": "2024-06-14",
        }
        
        body: Dict[str, Any] = {
            "title": parameters["title"].strip(),
            "slug": parameters["slug"].strip(),
            "lengthInMinutes": parameters["lengthInMinutes"],
        }
        
        description = parameters.get("description")
        if description is not None and description != "":
            body["description"] = description
        
        for key in [
            "slotInterval",
            "minimumBookingNotice",
            "beforeEventBuffer",
            "afterEventBuffer",
            "scheduleId",
        ]:
            value = parameters.get(key)
            if value is not None:
                body[key] = value
        
        disable_guests = parameters.get("disableGuests")
        if disable_guests is not None:
            body["disableGuests"] = disable_guests
        
        url = "https://api.cal.com/v2/event-types"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
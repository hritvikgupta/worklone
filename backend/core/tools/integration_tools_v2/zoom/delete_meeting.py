from typing import Any, Dict
import httpx
from urllib.parse import quote, urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZoomDeleteMeetingTool(BaseTool):
    name = "zoom_delete_meeting"
    description = "Delete or cancel a Zoom meeting"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ZOOM_ACCESS_TOKEN",
                description="Access token",
                env_var="ZOOM_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "zoom",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("ZOOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "meetingId": {
                    "type": "string",
                    "description": "The meeting ID to delete (e.g., \"1234567890\" or \"85746065432\")",
                },
                "occurrenceId": {
                    "type": "string",
                    "description": "Occurrence ID for deleting a specific occurrence of a recurring meeting",
                },
                "scheduleForReminder": {
                    "type": "boolean",
                    "description": "Send cancellation reminder email to registrants",
                },
                "cancelMeetingReminder": {
                    "type": "boolean",
                    "description": "Send cancellation email to registrants and alternative hosts",
                },
            },
            "required": ["meetingId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        meeting_id = parameters["meetingId"]
        base_url = f"https://api.zoom.us/v2/meetings/{quote(meeting_id)}"

        query_params = {}
        occurrence_id = parameters.get("occurrenceId")
        if occurrence_id:
            query_params["occurrence_id"] = occurrence_id
        schedule_for_reminder = parameters.get("scheduleForReminder")
        if schedule_for_reminder is not None:
            query_params["schedule_for_reminder"] = str(schedule_for_reminder).lower()
        cancel_meeting_reminder = parameters.get("cancelMeetingReminder")
        if cancel_meeting_reminder is not None:
            query_params["cancel_meeting_reminder"] = str(cancel_meeting_reminder).lower()

        query_string = urlencode(query_params)
        url = f"{base_url}?{query_string}" if query_params else base_url

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except:
                        data = {}
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
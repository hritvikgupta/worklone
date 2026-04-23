from typing import Any, Dict
import httpx
import urllib.parse
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZoomUpdateMeetingTool(BaseTool):
    name = "zoom_update_meeting"
    description = "Update an existing Zoom meeting"
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
            context_token_keys=("zoom_token",},
            env_token_keys=("ZOOM_ACCESS_TOKEN",},
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
                    "description": 'The meeting ID to update (e.g., "1234567890" or "85746065432")',
                },
                "topic": {
                    "type": "string",
                    "description": 'Meeting topic (e.g., "Weekly Team Standup" or "Project Review")',
                },
                "type": {
                    "type": "number",
                    "description": "Meeting type: 1=instant, 2=scheduled, 3=recurring no fixed time, 8=recurring fixed time",
                },
                "startTime": {
                    "type": "string",
                    "description": "Meeting start time in ISO 8601 format (e.g., 2025-06-03T10:00:00Z)",
                },
                "duration": {
                    "type": "number",
                    "description": "Meeting duration in minutes (e.g., 30, 60, 90)",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for the meeting (e.g., America/Los_Angeles)",
                },
                "password": {
                    "type": "string",
                    "description": "Meeting password",
                },
                "agenda": {
                    "type": "string",
                    "description": "Meeting agenda or description text",
                },
                "hostVideo": {
                    "type": "boolean",
                    "description": "Start with host video on",
                },
                "participantVideo": {
                    "type": "boolean",
                    "description": "Start with participant video on",
                },
                "joinBeforeHost": {
                    "type": "boolean",
                    "description": "Allow participants to join before host",
                },
                "muteUponEntry": {
                    "type": "boolean",
                    "description": "Mute participants upon entry",
                },
                "waitingRoom": {
                    "type": "boolean",
                    "description": "Enable waiting room",
                },
                "autoRecording": {
                    "type": "string",
                    "description": "Auto recording setting: local, cloud, or none",
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
        url = f"https://api.zoom.us/v2/meetings/{urllib.parse.quote(str(meeting_id))}"
        
        body: Dict[str, Any] = {}
        if parameters.get("topic"):
            body["topic"] = parameters["topic"]
        if parameters.get("type") is not None:
            body["type"] = parameters["type"]
        if parameters.get("startTime"):
            body["start_time"] = parameters["startTime"]
        if parameters.get("duration") is not None:
            body["duration"] = parameters["duration"]
        if parameters.get("timezone"):
            body["timezone"] = parameters["timezone"]
        if parameters.get("password"):
            body["password"] = parameters["password"]
        if parameters.get("agenda"):
            body["agenda"] = parameters["agenda"]

        settings: Dict[str, Any] = {}
        if parameters.get("hostVideo") is not None:
            settings["host_video"] = parameters["hostVideo"]
        if parameters.get("participantVideo") is not None:
            settings["participant_video"] = parameters["participantVideo"]
        if parameters.get("joinBeforeHost") is not None:
            settings["join_before_host"] = parameters["joinBeforeHost"]
        if parameters.get("muteUponEntry") is not None:
            settings["mute_upon_entry"] = parameters["muteUponEntry"]
        if parameters.get("waitingRoom") is not None:
            settings["waiting_room"] = parameters["waitingRoom"]
        if parameters.get("autoRecording"):
            settings["auto_recording"] = parameters["autoRecording"]

        if settings:
            body["settings"] = settings
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    if response.status_code == 204:
                        return ToolResult(success=True, output="Meeting updated successfully.", data={"success": True})
                    else:
                        return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"Zoom API error: {response.status_code} {response.reason_phrase}")
                    except Exception:
                        error_msg = f"Zoom API error: {response.status_code} {response.reason_phrase}"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
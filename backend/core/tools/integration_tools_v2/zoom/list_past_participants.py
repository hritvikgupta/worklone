from typing import Any, Dict
import httpx
import json
from urllib.parse import quote, urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZoomListPastParticipantsTool(BaseTool):
    name = "zoom_list_past_participants"
    description = "List participants from a past Zoom meeting"
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
            context_token_keys=("ZOOM_ACCESS_TOKEN",),
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
                    "description": 'The past meeting ID or UUID (e.g., "1234567890" or "4444AAABBBccccc12345==")',
                },
                "pageSize": {
                    "type": "number",
                    "description": "Number of records per page, 1-300 (e.g., 30, 50, 100)",
                },
                "nextPageToken": {
                    "type": "string",
                    "description": "Token for pagination to get next page of results",
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
        base_url = f"https://api.zoom.us/v2/past_meetings/{quote(meeting_id)}/participants"
        
        query_dict: Dict[str, Any] = {}
        page_size = parameters.get("pageSize")
        if page_size is not None:
            query_dict["page_size"] = page_size
        next_page_token = parameters.get("nextPageToken")
        if next_page_token is not None:
            query_dict["next_page_token"] = next_page_token
        
        query_string = urlencode(query_dict)
        url = f"{base_url}?{query_string}" if query_string else base_url
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    participants = []
                    for participant in data.get("participants", []):
                        participants.append({
                            "id": participant.get("id"),
                            "user_id": participant.get("user_id"),
                            "name": participant.get("name"),
                            "user_email": participant.get("user_email"),
                            "join_time": participant.get("join_time"),
                            "leave_time": participant.get("leave_time"),
                            "duration": participant.get("duration"),
                            "attentiveness_score": participant.get("attentiveness_score"),
                            "failover": participant.get("failover"),
                            "status": participant.get("status"),
                        })
                    page_info = {
                        "pageSize": data.get("page_size", 0),
                        "totalRecords": data.get("total_records", 0),
                        "nextPageToken": data.get("next_page_token"),
                    }
                    output_data = {
                        "participants": participants,
                        "pageInfo": page_info,
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data, indent=2),
                        data=output_data,
                    )
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("message", f"Zoom API error: {response.status_code} {response.reason}")
                    except Exception:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
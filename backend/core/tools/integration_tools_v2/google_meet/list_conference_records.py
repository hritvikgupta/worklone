from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleMeetListConferenceRecordsTool(BaseTool):
    name = "google_meet_list_conference_records"
    description = "List conference records for meetings you organized"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_MEET_ACCESS_TOKEN",
                description="Access token for Google Meet API",
                env_var="GOOGLE_MEET_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-meet",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_MEET_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": 'Filter by space name (e.g., space.name = "spaces/abc123") or time range (e.g., start_time > "2024-01-01T00:00:00Z")',
                },
                "pageSize": {
                    "type": "number",
                    "description": "Maximum number of conference records to return (max 100)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token from a previous list request",
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
        
        url = "https://meet.googleapis.com/v2/conferenceRecords"
        params: Dict[str, Any] = {}
        if parameters.get("filter"):
            params["filter"] = parameters["filter"]
        if parameters.get("pageSize") is not None:
            params["pageSize"] = parameters["pageSize"]
        if parameters.get("pageToken"):
            params["pageToken"] = parameters["pageToken"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if 200 <= response.status_code < 300:
                    api_data = response.json()
                    records = api_data.get("conferenceRecords", [])
                    transformed_records = [
                        {
                            "name": record.get("name"),
                            "startTime": record.get("startTime"),
                            "endTime": record.get("endTime"),
                            "expireTime": record.get("expireTime"),
                            "space": record.get("space"),
                        }
                        for record in records
                    ]
                    result_data = {
                        "conferenceRecords": transformed_records,
                        "nextPageToken": api_data.get("nextPageToken"),
                    }
                    return ToolResult(success=True, output=response.text, data=result_data)
                else:
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Google Meet API error ({response.status_code}): {error_text}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
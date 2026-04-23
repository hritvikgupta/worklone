from typing import Any, Dict
import httpx
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleMeetListParticipantsTool(BaseTool):
    name = "Google Meet List Participants"
    description = "List participants of a conference record"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="access_token",
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
            context_token_keys=("access_token",),
            env_token_keys=("GOOGLE_MEET_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "conferenceName": {
                    "type": "string",
                    "description": "Conference record resource name (e.g., conferenceRecords/abc123)",
                },
                "filter": {
                    "type": "string",
                    "description": 'Filter participants (e.g., earliest_start_time > "2024-01-01T00:00:00Z")',
                },
                "pageSize": {
                    "type": "number",
                    "description": "Maximum number of participants to return (default 100, max 250)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token from a previous list request",
                },
            },
            "required": ["conferenceName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        conference_name = parameters["conferenceName"].strip()
        if not conference_name.startswith("conferenceRecords/"):
            conference_name = f"conferenceRecords/{conference_name}"
        
        url = f"https://meet.googleapis.com/v2/{conference_name}/participants"
        
        query_params_dict = {}
        filter_val = parameters.get("filter")
        if filter_val:
            query_params_dict["filter"] = filter_val
        page_size = parameters.get("pageSize")
        if page_size is not None:
            query_params_dict["pageSize"] = str(page_size)
        page_token = parameters.get("pageToken")
        if page_token:
            query_params_dict["pageToken"] = page_token
        
        if query_params_dict:
            url += "?" + urlencode(query_params_dict)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200]:
                    data = response.json()
                    participants = data.get("participants", [])
                    
                    def get_display_name(p: dict) -> str | None:
                        return (
                            p.get("signedinUser", {}).get("displayName") or
                            p.get("anonymousUser", {}).get("displayName") or
                            p.get("phoneUser", {}).get("displayName") or
                            None
                        )
                    
                    def get_user_type(p: dict) -> str:
                        if p.get("signedinUser"):
                            return "signed_in"
                        if p.get("anonymousUser"):
                            return "anonymous"
                        if p.get("phoneUser"):
                            return "phone"
                        return "unknown"
                    
                    participants_mapped = [
                        {
                            "name": p["name"],
                            "earliestStartTime": p["earliestStartTime"],
                            "latestEndTime": p.get("latestEndTime"),
                            "displayName": get_display_name(p),
                            "userType": get_user_type(p),
                        }
                        for p in participants
                    ]
                    
                    transformed = {
                        "participants": participants_mapped,
                        "nextPageToken": data.get("nextPageToken"),
                        "totalSize": data.get("totalSize"),
                    }
                    output_str = json.dumps(transformed, indent=2)
                    return ToolResult(success=True, output=output_str, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
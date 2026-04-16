from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LumaUpdateEventTool(BaseTool):
    name = "luma_update_event"
    description = "Update an existing Luma event. Only the fields you provide will be changed; all other fields remain unchanged."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LUMA_API_KEY",
                description="Luma API key",
                env_var="LUMA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Luma API key",
                },
                "eventId": {
                    "type": "string",
                    "description": "Event ID to update (starts with evt-)",
                },
                "name": {
                    "type": "string",
                    "description": "New event name/title",
                },
                "startAt": {
                    "type": "string",
                    "description": "New start time in ISO 8601 format (e.g., 2025-03-15T18:00:00Z)",
                },
                "timezone": {
                    "type": "string",
                    "description": "New IANA timezone (e.g., America/New_York, Europe/London)",
                },
                "endAt": {
                    "type": "string",
                    "description": "New end time in ISO 8601 format (e.g., 2025-03-15T20:00:00Z)",
                },
                "durationInterval": {
                    "type": "string",
                    "description": "New duration as ISO 8601 interval (e.g., PT2H for 2 hours). Used if endAt is not provided.",
                },
                "descriptionMd": {
                    "type": "string",
                    "description": "New event description in Markdown format",
                },
                "meetingUrl": {
                    "type": "string",
                    "description": "New virtual meeting URL (e.g., Zoom, Google Meet link)",
                },
                "visibility": {
                    "type": "string",
                    "description": "New visibility: public, members-only, or private",
                },
                "coverUrl": {
                    "type": "string",
                    "description": "New cover image URL (must be a Luma CDN URL from images.lumacdn.com)",
                },
            },
            "required": ["apiKey", "eventId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("LUMA_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Luma API key not configured.")
        
        headers = {
            "x-luma-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        body = {"id": parameters["eventId"].strip()}
        name = parameters.get("name")
        if name:
            body["name"] = name
        start_at = parameters.get("startAt")
        if start_at:
            body["start_at"] = start_at
        timezone = parameters.get("timezone")
        if timezone:
            body["timezone"] = timezone
        end_at = parameters.get("endAt")
        if end_at:
            body["end_at"] = end_at
        duration_interval = parameters.get("durationInterval")
        if duration_interval:
            body["duration_interval"] = duration_interval
        description_md = parameters.get("descriptionMd")
        if description_md:
            body["description_md"] = description_md
        meeting_url = parameters.get("meetingUrl")
        if meeting_url:
            body["meeting_url"] = meeting_url
        visibility = parameters.get("visibility")
        if visibility:
            body["visibility"] = visibility
        cover_url = parameters.get("coverUrl")
        if cover_url:
            body["cover_url"] = cover_url
        
        url = "https://public-api.luma.com/v1/event/update"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
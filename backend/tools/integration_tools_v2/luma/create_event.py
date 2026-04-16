from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LumaCreateEventTool(BaseTool):
    name = "luma_create_event"
    description = "Create a new event on Luma with a name, start time, timezone, and optional details like description, location, and visibility."
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        token = context.get("LUMA_API_KEY") if context else None
        token = token or os.getenv("LUMA_API_KEY", "")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Event name/title",
                },
                "startAt": {
                    "type": "string",
                    "description": "Event start time in ISO 8601 format (e.g., 2025-03-15T18:00:00Z)",
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone (e.g., America/New_York, Europe/London)",
                },
                "endAt": {
                    "type": "string",
                    "description": "Event end time in ISO 8601 format (e.g., 2025-03-15T20:00:00Z)",
                },
                "durationInterval": {
                    "type": "string",
                    "description": "Event duration as ISO 8601 interval (e.g., PT2H for 2 hours, PT30M for 30 minutes). Used if endAt is not provided.",
                },
                "descriptionMd": {
                    "type": "string",
                    "description": "Event description in Markdown format",
                },
                "meetingUrl": {
                    "type": "string",
                    "description": "Virtual meeting URL for online events (e.g., Zoom, Google Meet link)",
                },
                "visibility": {
                    "type": "string",
                    "description": "Event visibility: public, members-only, or private (defaults to public)",
                },
                "coverUrl": {
                    "type": "string",
                    "description": "Cover image URL (must be a Luma CDN URL from images.lumacdn.com)",
                },
            },
            "required": ["name", "startAt", "timezone"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Luma API key not configured.")

        headers = {
            "x-luma-api-key": api_key,
            "Content-Type": "application/json",
        }

        body = {
            "name": parameters["name"],
            "start_at": parameters["startAt"],
            "timezone": parameters["timezone"],
        }
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

        url = "https://public-api.luma.com/v1/event/create"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
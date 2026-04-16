from typing import Any, Dict
import httpx
import time
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsTimezoneTool(BaseTool):
    name = "google_maps_timezone"
    description = "Get timezone information for a location"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_CLOUD_API_KEY",
                description="Google Maps API key",
                env_var="GOOGLE_CLOUD_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = None
        if context is not None:
            api_key = context.get("GOOGLE_CLOUD_API_KEY")
        if api_key is None:
            api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
        return (api_key or "").strip()

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "Latitude coordinate",
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude coordinate",
                },
                "timestamp": {
                    "type": "number",
                    "description": "Unix timestamp to determine DST offset (defaults to current time)",
                },
                "language": {
                    "type": "string",
                    "description": "Language code for timezone name (e.g., en, es, fr)",
                },
            },
            "required": ["lat", "lng"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        lat = parameters["lat"]
        lng = parameters["lng"]
        timestamp = parameters.get("timestamp")
        if timestamp is None:
            timestamp = int(time.time())
        else:
            timestamp = int(timestamp)
        language = parameters.get("language")

        query_params = {
            "location": f"{lat},{lng}",
            "timestamp": str(timestamp),
            "key": api_key,
        }
        if language:
            query_params["language"] = str(language).strip()

        headers = {
            "Content-Type": "application/json",
        }
        url = "https://maps.googleapis.com/maps/api/timezone/json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if data.get("status") != "OK":
                    error_msg = data.get("errorMessage", "Unknown error")
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Timezone request failed: {data['status']} - {error_msg}",
                    )

                raw_offset = data["rawOffset"]
                dst_offset = data["dstOffset"]
                total_offset_seconds = raw_offset + dst_offset
                total_offset_hours = total_offset_seconds / 3600

                output_data = {
                    "timeZoneId": data["timeZoneId"],
                    "timeZoneName": data["timeZoneName"],
                    "rawOffset": raw_offset,
                    "dstOffset": dst_offset,
                    "totalOffsetSeconds": total_offset_seconds,
                    "totalOffsetHours": total_offset_hours,
                }

                return ToolResult(
                    success=True,
                    output=str(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
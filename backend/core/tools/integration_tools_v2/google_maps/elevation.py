from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsElevationTool(BaseTool):
    name = "Google Maps Elevation"
    description = "Get elevation data for a location"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Google Maps API key",
                env_var="GOOGLE_CLOUD_API_KEY",
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
                    "description": "Google Maps API key",
                },
                "lat": {
                    "type": "number",
                    "description": "Latitude coordinate",
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude coordinate",
                },
            },
            "required": ["apiKey", "lat", "lng"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("apiKey") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Google Maps API key not configured.")

        lat = parameters["lat"]
        lng = parameters["lng"]
        url = "https://maps.googleapis.com/maps/api/elevation/json"
        query_params = {
            "locations": f"{lat},{lng}",
            "key": api_key.strip(),
        }
        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code not in [200]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if data.get("status") != "OK":
                    status = data.get("status")
                    error_message = data.get("error_message") or "Unknown error"
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Elevation request failed: {status} - {error_message}",
                    )

                result = data["results"][0]
                output_data = {
                    "elevation": result["elevation"],
                    "lat": result["location"]["lat"],
                    "lng": result["location"]["lng"],
                    "resolution": result["resolution"],
                }
                return ToolResult(success=True, output=str(output_data), data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
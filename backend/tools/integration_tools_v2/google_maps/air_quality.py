from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleMapsAirQualityTool(BaseTool):
    name = "google_maps_air_quality"
    description = "Get current air quality data for a location"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_CLOUD_API_KEY",
                description="Google Maps API key with Air Quality API enabled",
                env_var="GOOGLE_CLOUD_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google_cloud",
            context=context,
            context_token_keys=("GOOGLE_CLOUD_API_KEY",),
            env_token_keys=("GOOGLE_CLOUD_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

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
                "languageCode": {
                    "type": "string",
                    "description": 'Language code for the response (e.g., "en", "es")',
                },
            },
            "required": ["lat", "lng"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        url = f"https://airquality.googleapis.com/v1/currentConditions:lookup?key={access_token.strip()}"
        
        body = {
            "location": {
                "latitude": parameters["lat"],
                "longitude": parameters["lng"],
            },
            "extraComputations": [
                "HEALTH_RECOMMENDATIONS",
                "DOMINANT_POLLUTANT_CONCENTRATION",
                "POLLUTANT_CONCENTRATION",
                "LOCAL_AQI",
                "POLLUTANT_ADDITIONAL_INFO",
            ],
        }
        language_code = parameters.get("languageCode")
        if language_code:
            body["languageCode"] = str(language_code).strip()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsGeocodeTool(BaseTool):
    name = "google_maps_geocode"
    description = "Convert an address into geographic coordinates (latitude and longitude)"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Google Maps API key",
                },
                "address": {
                    "type": "string",
                    "description": "The address to geocode",
                },
                "language": {
                    "type": "string",
                    "description": "Language code for results (e.g., en, es, fr)",
                },
                "region": {
                    "type": "string",
                    "description": "Region bias as a ccTLD code (e.g., us, uk)",
                },
            },
            "required": ["apiKey", "address"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey", "").strip()
        if self._is_placeholder_token(api_key):
            api_key = ""
            if context and "GOOGLE_CLOUD_API_KEY" in context:
                context_key = context["GOOGLE_CLOUD_API_KEY"].strip()
                if not self._is_placeholder_token(context_key):
                    api_key = context_key

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Google Maps API key not configured.")

        address = parameters.get("address", "").strip()
        if not address:
            return ToolResult(success=False, output="", error="Address is required.")

        query_params: dict[str, str] = {
            "address": address,
            "key": api_key,
        }
        language = parameters.get("language")
        if language:
            query_params["language"] = str(language).strip()
        region = parameters.get("region")
        if region:
            query_params["region"] = str(region).strip()

        headers = {
            "Content-Type": "application/json",
        }
        url = "https://maps.googleapis.com/maps/api/geocode/json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=query_params, headers=headers)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if data.get("status") != "OK":
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Geocoding failed: {data.get('status', 'Unknown')} - {data.get('error_message', 'Unknown error')}",
                    )

                results = data.get("results", [])
                if not results:
                    return ToolResult(success=False, output="", error="No geocoding results found.")

                result = results[0]
                geometry = result.get("geometry", {})
                location = geometry.get("location", {})

                output_data = {
                    "formattedAddress": result.get("formatted_address", ""),
                    "lat": location.get("lat"),
                    "lng": location.get("lng"),
                    "location": {
                        "lat": location.get("lat"),
                        "lng": location.get("lng"),
                    },
                    "placeId": result.get("place_id", ""),
                    "addressComponents": [
                        {
                            "longName": comp.get("long_name", ""),
                            "shortName": comp.get("short_name", ""),
                            "types": comp.get("types", []),
                        }
                        for comp in result.get("address_components", [])
                    ],
                    "locationType": geometry.get("location_type", ""),
                }

                return ToolResult(success=True, output=str(output_data), data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
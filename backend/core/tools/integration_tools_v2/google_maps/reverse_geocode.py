from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsReverseGeocodeTool(BaseTool):
    name = "google_maps_reverse_geocode"
    description = "Convert geographic coordinates (latitude and longitude) into a human-readable address"
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
                "lat": {
                    "type": "number",
                    "description": "Latitude coordinate",
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude coordinate",
                },
                "language": {
                    "type": "string",
                    "description": "Language code for results (e.g., en, es, fr)",
                },
            },
            "required": ["lat", "lng"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = context.get("GOOGLE_CLOUD_API_KEY") if context else None
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Google Cloud API key not configured.")

        headers = {
            "Content-Type": "application/json",
        }

        url = "https://maps.googleapis.com/maps/api/geocode/json"

        params_dict: Dict[str, str] = {
            "latlng": f"{parameters['lat']},{parameters['lng']}",
            "key": api_key.strip(),
        }
        language = parameters.get("language")
        if language:
            params_dict["language"] = str(language).strip()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data: Dict[str, Any] = response.json()

                if data.get("status") != "OK":
                    status = data.get("status", "Unknown")
                    error_msg = data.get("error_message", "Unknown error")
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Reverse geocoding failed: {status} - {error_msg}",
                    )

                results = data.get("results", [])
                if not results:
                    return ToolResult(success=False, output="", error="No geocoding results found.")

                result = results[0]

                output_data: Dict[str, Any] = {
                    "formattedAddress": result.get("formatted_address", ""),
                    "placeId": result.get("place_id", ""),
                    "addressComponents": [
                        {
                            "longName": comp["long_name"],
                            "shortName": comp["short_name"],
                            "types": comp["types"],
                        }
                        for comp in result.get("address_components", [])
                    ],
                    "types": result.get("types", []),
                }

                return ToolResult(
                    success=True,
                    output=output_data["formattedAddress"],
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsPlacesSearchTool(BaseTool):
    name = "google_maps_places_search"
    description = "Search for places using a text query"
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
        if context is None:
            return ""
        return context.get("GOOGLE_CLOUD_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., \"restaurants in Times Square\")",
                },
                "location": {
                    "type": "object",
                    "description": "Location to bias results towards ({lat, lng})",
                    "properties": {
                        "lat": {"type": "number"},
                        "lng": {"type": "number"},
                    },
                    "additionalProperties": False,
                },
                "radius": {
                    "type": "number",
                    "description": "Search radius in meters",
                },
                "type": {
                    "type": "string",
                    "description": "Place type filter (e.g., restaurant, cafe, hotel)",
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
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Google Maps API key not configured.")

        headers = {
            "Content-Type": "application/json",
        }

        base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        query_params: Dict[str, Any] = {
            "query": parameters["query"].strip(),
            "key": api_key.strip(),
        }

        location = parameters.get("location")
        if location:
            query_params["location"] = f"{location['lat']},{location['lng']}"

        radius = parameters.get("radius")
        if radius is not None:
            query_params["radius"] = str(radius)

        place_type = parameters.get("type")
        if place_type:
            query_params["type"] = place_type

        language = parameters.get("language")
        if language:
            query_params["language"] = language.strip()

        region = parameters.get("region")
        if region:
            query_params["region"] = region.strip()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=query_params)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                status = data.get("status")
                if status not in ["OK", "ZERO_RESULTS"]:
                    error_msg = data.get("error_message", "Unknown error")
                    return ToolResult(
                        success=False, output="", error=f"Places search failed: {status} - {error_msg}"
                    )

                places = []
                for place in data.get("results", []):
                    photos = place.get("photos", [])
                    photo_reference = photos[0].get("photo_reference") if photos else None
                    opening_hours = place.get("opening_hours", {})
                    places.append({
                        "placeId": place.get("place_id"),
                        "name": place.get("name"),
                        "formattedAddress": place.get("formatted_address"),
                        "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                        "lng": place.get("geometry", {}).get("location", {}).get("lng"),
                        "types": place.get("types", []),
                        "rating": place.get("rating"),
                        "userRatingsTotal": place.get("user_ratings_total"),
                        "priceLevel": place.get("price_level"),
                        "openNow": opening_hours.get("open_now"),
                        "photoReference": photo_reference,
                        "businessStatus": place.get("business_status"),
                    })

                result = {
                    "places": places,
                    "nextPageToken": data.get("next_page_token"),
                }
                return ToolResult(success=True, output=response.text, data=result)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
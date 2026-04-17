from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsPlaceDetailsTool(BaseTool):
    name = "Google Maps Place Details"
    description = "Get detailed information about a specific place"
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

    def _get_api_key(self, parameters: dict, context: dict | None) -> str:
        candidates = [
            parameters.get("apiKey"),
            context.get("GOOGLE_CLOUD_API_KEY") if context else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and not self._is_placeholder_token(candidate):
                return candidate.strip()
        raise ValueError("Google Maps API key not configured.")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Google Maps API key",
                },
                "placeId": {
                    "type": "string",
                    "description": "Google Place ID",
                },
                "fields": {
                    "type": "string",
                    "description": "Comma-separated list of fields to return",
                },
                "language": {
                    "type": "string",
                    "description": "Language code for results (e.g., en, es, fr)",
                },
            },
            "required": ["apiKey", "placeId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            api_key = self._get_api_key(parameters, context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        headers = {
            "Content-Type": "application/json",
        }

        url = "https://maps.googleapis.com/maps/api/place/details/json"

        query_params: Dict[str, str] = {
            "place_id": parameters["placeId"].strip(),
            "key": api_key,
        }

        fields = parameters.get("fields")
        if not fields:
            fields = (
                "place_id,name,formatted_address,geometry,types,rating,user_ratings_total,"
                "price_level,website,formatted_phone_number,international_phone_number,"
                "opening_hours,reviews,photos,url,utc_offset,vicinity,business_status"
            )
        query_params["fields"] = fields

        language = parameters.get("language")
        if language:
            query_params["language"] = language.strip()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code != 200:
                    return ToolResult(
                        success=False, output="", error=response.text
                    )

                data = response.json()

                if data.get("status") != "OK":
                    error_msg = data.get("error_message", "Unknown error")
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Place details request failed: {data['status']} - {error_msg}",
                    )

                place = data.get("result", {})

                reviews_raw = place.get("reviews", [])
                reviews = []
                for review in reviews_raw:
                    reviews.append({
                        "authorName": review.get("author_name"),
                        "authorUrl": review.get("author_url"),
                        "profilePhotoUrl": review.get("profile_photo_url"),
                        "rating": review.get("rating"),
                        "text": review.get("text"),
                        "time": review.get("time"),
                        "relativeTimeDescription": review.get("relative_time_description"),
                    })

                photos_raw = place.get("photos", [])
                photos = []
                for photo in photos_raw:
                    photos.append({
                        "photoReference": photo.get("photo_reference"),
                        "height": photo.get("height"),
                        "width": photo.get("width"),
                        "htmlAttributions": photo.get("html_attributions", []),
                    })

                opening_hours = place.get("opening_hours", {})
                open_now = opening_hours.get("open_now")
                weekday_text = opening_hours.get("weekday_text", [])

                location = place.get("geometry", {}).get("location", {})
                lat = location.get("lat")
                lng = location.get("lng")

                transformed = {
                    "placeId": place.get("place_id"),
                    "name": place.get("name"),
                    "formattedAddress": place.get("formatted_address"),
                    "lat": lat,
                    "lng": lng,
                    "types": place.get("types", []),
                    "rating": place.get("rating"),
                    "userRatingsTotal": place.get("user_ratings_total"),
                    "priceLevel": place.get("price_level"),
                    "website": place.get("website"),
                    "phoneNumber": place.get("formatted_phone_number"),
                    "internationalPhoneNumber": place.get("international_phone_number"),
                    "openNow": open_now,
                    "weekdayText": weekday_text,
                    "reviews": reviews,
                    "photos": photos,
                    "url": place.get("url"),
                    "utcOffset": place.get("utc_offset"),
                    "vicinity": place.get("vicinity"),
                    "businessStatus": place.get("business_status"),
                }

                return ToolResult(
                    success=True, output=response.text, data=transformed
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import re
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsDirectionsTool(BaseTool):
    name = "google_maps_directions"
    description = "Get directions and route information between two locations"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Google Maps API key",
                },
                "origin": {
                    "type": "string",
                    "description": "Starting location (address or lat,lng)",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination location (address or lat,lng)",
                },
                "mode": {
                    "type": "string",
                    "description": "Travel mode: driving, walking, bicycling, or transit",
                },
                "avoid": {
                    "type": "string",
                    "description": "Features to avoid: tolls, highways, or ferries",
                },
                "waypoints": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Array of intermediate waypoints",
                },
                "units": {
                    "type": "string",
                    "description": "Unit system: metric or imperial",
                },
                "language": {
                    "type": "string",
                    "description": "Language code for results (e.g., en, es, fr)",
                },
            },
            "required": ["apiKey", "origin", "destination"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (parameters.get("apiKey") or "").strip()
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Google Maps API key not configured.")

        query_params = {
            "origin": (parameters.get("origin") or "").strip(),
            "destination": (parameters.get("destination") or "").strip(),
            "key": api_key,
        }

        mode = parameters.get("mode")
        if mode:
            query_params["mode"] = mode

        avoid = parameters.get("avoid")
        if avoid:
            query_params["avoid"] = avoid

        waypoints = parameters.get("waypoints")
        if isinstance(waypoints, list) and waypoints:
            waypoint_strs = [str(wp).strip() for wp in waypoints if wp and str(wp).strip()]
            if waypoint_strs:
                query_params["waypoints"] = "|".join(waypoint_strs)

        units = parameters.get("units")
        if units:
            query_params["units"] = units

        language = (parameters.get("language") or "").strip()
        if language:
            query_params["language"] = language

        url = "https://maps.googleapis.com/maps/api/directions/json"
        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=query_params, headers=headers)

                if response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"HTTP error {response.status_code}: {response.text}",
                    )

                try:
                    data = response.json()
                except ValueError:
                    return ToolResult(
                        success=False,
                        output=response.text,
                        error="Invalid JSON response from API",
                    )

                if data.get("status") != "OK":
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Directions request failed: {data.get('status')} - {data.get('error_message', 'Unknown error')}",
                    )

                transformed_routes = []
                for route in data.get("routes", []):
                    transformed_legs = []
                    for leg in route.get("legs", []):
                        transformed_steps = []
                        for step in leg.get("steps", []):
                            instruction = re.sub(r"<[^>]*>", "", step.get("html_instructions", ""))
                            transformed_steps.append({
                                "instruction": instruction,
                                "distanceText": step["distance"]["text"],
                                "distanceMeters": step["distance"]["value"],
                                "durationText": step["duration"]["text"],
                                "durationSeconds": step["duration"]["value"],
                                "startLocation": {
                                    "lat": step["start_location"]["lat"],
                                    "lng": step["start_location"]["lng"],
                                },
                                "endLocation": {
                                    "lat": step["end_location"]["lat"],
                                    "lng": step["end_location"]["lng"],
                                },
                                "travelMode": step["travel_mode"],
                                "maneuver": step.get("maneuver"),
                            })
                        transformed_legs.append({
                            "startAddress": leg["start_address"],
                            "endAddress": leg["end_address"],
                            "startLocation": {
                                "lat": leg["start_location"]["lat"],
                                "lng": leg["start_location"]["lng"],
                            },
                            "endLocation": {
                                "lat": leg["end_location"]["lat"],
                                "lng": leg["end_location"]["lng"],
                            },
                            "distanceText": leg["distance"]["text"],
                            "distanceMeters": leg["distance"]["value"],
                            "durationText": leg["duration"]["text"],
                            "durationSeconds": leg["duration"]["value"],
                            "steps": transformed_steps,
                        })
                    transformed_routes.append({
                        "summary": route.get("summary", ""),
                        "legs": transformed_legs,
                        "overviewPolyline": route["overview_polyline"]["points"],
                        "warnings": route.get("warnings", []),
                        "waypointOrder": route.get("waypoint_order", []),
                    })

                primary_route = transformed_routes[0] if transformed_routes else None
                primary_leg = primary_route["legs"][0] if primary_route and primary_route.get("legs") else None

                output_data = {
                    "routes": transformed_routes,
                    "distanceText": primary_leg["distanceText"] if primary_leg else "",
                    "distanceMeters": primary_leg["distanceMeters"] if primary_leg else 0,
                    "durationText": primary_leg["durationText"] if primary_leg else "",
                    "durationSeconds": primary_leg["durationSeconds"] if primary_leg else 0,
                    "startAddress": primary_leg["startAddress"] if primary_leg else "",
                    "endAddress": primary_leg["endAddress"] if primary_leg else "",
                    "steps": primary_leg["steps"] if primary_leg else [],
                    "polyline": primary_route["overviewPolyline"] if primary_route else "",
                }

                output_str = json.dumps(output_data, indent=2)
                return ToolResult(success=True, output=output_str, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
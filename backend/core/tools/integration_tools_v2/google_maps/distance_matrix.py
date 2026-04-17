from typing import Any, Dict, List
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsDistanceMatrixTool(BaseTool):
    name = "google_maps_distance_matrix"
    description = "Calculate travel distance and time between multiple origins and destinations"
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
                    "description": "Origin location (address or lat,lng)",
                },
                "destinations": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": "Array of destination locations",
                },
                "mode": {
                    "type": "string",
                    "description": "Travel mode: driving, walking, bicycling, or transit",
                },
                "avoid": {
                    "type": "string",
                    "description": "Features to avoid: tolls, highways, or ferries",
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
            "required": ["apiKey", "origin", "destinations"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey", "")
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Google Maps API key not configured.")

        api_key = api_key.strip()
        origin = parameters["origin"].strip()
        destinations = parameters["destinations"]
        if not isinstance(destinations, list):
            return ToolResult(success=False, output="", error="destinations must be an array of strings.")

        dest_str = "|".join(str(dest).strip() for dest in destinations)

        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        query_params: Dict[str, str] = {
            "origins": origin,
            "destinations": dest_str,
            "key": api_key,
        }

        mode = parameters.get("mode")
        if mode:
            query_params["mode"] = str(mode)

        avoid = parameters.get("avoid")
        if avoid:
            query_params["avoid"] = str(avoid)

        units = parameters.get("units")
        if units:
            query_params["units"] = str(units)

        language = parameters.get("language")
        if language:
            query_params["language"] = str(language).strip()

        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if data.get("status") != "OK":
                    error_msg = data.get("error_message", "Unknown error")
                    return ToolResult(
                        success=False, output="", error=f"Distance matrix request failed: {data.get('status')} - {error_msg}"
                    )

                rows: List[Dict[str, List[Dict[str, Any]]]] = []
                for row in data.get("rows", []):
                    elements: List[Dict[str, Any]] = []
                    for element in row.get("elements", []):
                        el: Dict[str, Any] = {
                            "distanceText": element.get("distance", {}).get("text", "N/A"),
                            "distanceMeters": element.get("distance", {}).get("value", 0),
                            "durationText": element.get("duration", {}).get("text", "N/A"),
                            "durationSeconds": element.get("duration", {}).get("value", 0),
                            "status": element.get("status", ""),
                        }
                        duration_in_traffic = element.get("duration_in_traffic")
                        if duration_in_traffic:
                            el["durationInTrafficText"] = duration_in_traffic.get("text")
                            el["durationInTrafficSeconds"] = duration_in_traffic.get("value")
                        elements.append(el)
                    rows.append({"elements": elements})

                output_data = {
                    "originAddresses": data.get("origin_addresses", []),
                    "destinationAddresses": data.get("destination_addresses", []),
                    "rows": rows,
                }

                return ToolResult(success=True, output=response.text, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
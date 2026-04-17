from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsSnapToRoadsTool(BaseTool):
    name = "google_maps_snap_to_roads"
    description = "Snap GPS coordinates to the nearest road segment"
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
                    "description": "Google Maps API key with Roads API enabled",
                },
                "path": {
                    "type": "string",
                    "description": "Pipe-separated list of lat,lng coordinates (e.g., \"60.170880,24.942795|60.170879,24.942796\")",
                },
                "interpolate": {
                    "type": "boolean",
                    "description": "Whether to interpolate additional points along the road",
                },
            },
            "required": ["apiKey", "path"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (parameters.get("apiKey") or "").strip()
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Google Maps API key not configured.")

        path = (parameters.get("path") or "").strip()
        if not path:
            return ToolResult(success=False, output="", error="Path parameter is required.")

        interpolate = parameters.get("interpolate")
        query_params = {
            "path": path,
            "key": api_key,
        }
        if interpolate is not None:
            query_params["interpolate"] = str(interpolate).lower()

        headers = {
            "Content-Type": "application/json",
        }
        url = "https://roads.googleapis.com/v1/snapToRoads"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=query_params, headers=headers)

            if response.status_code not in [200, 201, 204]:
                return ToolResult(success=False, output="", error=response.text)

            try:
                data = response.json()
            except json.JSONDecodeError:
                return ToolResult(success=False, output=response.text, error="Invalid JSON response.")

            error_obj = data.get("error")
            if error_obj:
                error_msg = error_obj.get("message", "Unknown error")
                return ToolResult(success=False, output="", error=f"Snap to Roads failed: {error_msg}")

            snapped_points = []
            for point in data.get("snappedPoints", []):
                snapped_points.append({
                    "location": {
                        "lat": point["location"]["latitude"],
                        "lng": point["location"]["longitude"],
                    },
                    "originalIndex": point.get("originalIndex"),
                    "placeId": point["placeId"],
                })

            transformed = {
                "snappedPoints": snapped_points,
                "warningMessage": data.get("warningMessage"),
            }
            output = json.dumps(transformed)
            return ToolResult(success=True, output=output, data=transformed)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
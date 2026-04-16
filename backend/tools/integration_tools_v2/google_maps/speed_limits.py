from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsSpeedLimitsTool(BaseTool):
    name = "google_maps_speed_limits"
    description = "Get speed limits for road segments. Requires either path coordinates or placeIds."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="api_key",
                description="Google Maps API key with Roads API enabled",
                env_var="GOOGLE_MAPS_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> str:
        api_key = None
        if context:
            api_key = context.get("api_key")
        if api_key is None:
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Pipe-separated list of lat,lng coordinates (required if placeIds not provided)",
                },
                "placeIds": {
                    "type": "array",
                    "description": "Array of Place IDs for road segments (required if path not provided)",
                    "items": {
                        "type": "string",
                    },
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Google Maps API key not configured.")

        path = parameters.get("path")
        place_ids = parameters.get("placeIds", [])
        has_path = path is not None and bool(path.strip())
        has_place_ids = bool(place_ids)

        if not has_path and not has_place_ids:
            return ToolResult(
                success=False,
                output="",
                error="Speed Limits requires either a path (coordinates) or placeIds. Please provide at least one.",
            )

        params: dict[str, str | list[str]] = {"key": api_key.strip()}
        if has_path:
            params["path"] = path.strip()
        if has_place_ids:
            params["placeId"] = [str(place_id).strip() for place_id in place_ids if str(place_id).strip()]

        headers = {
            "Content-Type": "application/json",
        }
        url = "https://roads.googleapis.com/v1/speedLimits"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
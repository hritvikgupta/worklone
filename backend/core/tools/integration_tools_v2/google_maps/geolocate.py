from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsGeolocateTool(BaseTool):
    name = "google_maps_geolocate"
    description = "Geolocate a device using WiFi access points, cell towers, or IP address"
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
                    "description": "Google Maps API key with Geolocation API enabled",
                },
                "homeMobileCountryCode": {
                    "type": "number",
                    "description": "Home mobile country code (MCC)",
                },
                "homeMobileNetworkCode": {
                    "type": "number",
                    "description": "Home mobile network code (MNC)",
                },
                "radioType": {
                    "type": "string",
                    "description": "Radio type: lte, gsm, cdma, wcdma, or nr",
                },
                "carrier": {
                    "type": "string",
                    "description": "Carrier name",
                },
                "considerIp": {
                    "type": "boolean",
                    "description": "Whether to use IP address for geolocation (default: true)",
                },
                "cellTowers": {
                    "type": "array",
                    "description": "Array of cell tower objects with cellId, locationAreaCode, mobileCountryCode, mobileNetworkCode",
                },
                "wifiAccessPoints": {
                    "type": "array",
                    "description": "Array of WiFi access point objects with macAddress (required), signalStrength, etc.",
                },
            },
            "required": ["apiKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key_raw = parameters.get("apiKey")
        if not api_key_raw or self._is_placeholder_token(str(api_key_raw)):
            return ToolResult(success=False, output="", error="Valid Google Maps API key is required.")

        api_key = str(api_key_raw).strip()
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={api_key}"

        body: Dict[str, Any] = {}
        number_bool_fields = ["homeMobileCountryCode", "homeMobileNetworkCode", "considerIp"]
        for field in number_bool_fields:
            if field in parameters and parameters[field] is not None:
                body[field] = parameters[field]

        string_fields = ["radioType", "carrier"]
        for field in string_fields:
            if field in parameters and parameters[field]:
                body[field] = parameters[field]

        array_fields = ["cellTowers", "wifiAccessPoints"]
        for field in array_fields:
            if field in parameters and parameters[field] and len(parameters[field]) > 0:
                body[field] = parameters[field]

        headers = {
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        if "error" in data:
                            error_msg = data["error"].get("message", "Unknown error")
                            return ToolResult(
                                success=False, output="", error=f"Geolocation failed: {error_msg}"
                            )
                        return ToolResult(success=True, output=response.text, data=data)
                    except Exception:
                        return ToolResult(success=True, output=response.text, data={})
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
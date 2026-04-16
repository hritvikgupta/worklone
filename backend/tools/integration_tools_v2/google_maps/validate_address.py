from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GoogleMapsValidateAddressTool(BaseTool):
    name = "google_maps_validate_address"
    description = "Validate and standardize a postal address"
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
                    "description": "Google Maps API key with Address Validation API enabled",
                },
                "address": {
                    "type": "string",
                    "description": "The address to validate (as a single string)",
                },
                "regionCode": {
                    "type": "string",
                    "description": "ISO 3166-1 alpha-2 country code (e.g., \"US\", \"CA\")",
                },
                "locality": {
                    "type": "string",
                    "description": "City or locality name",
                },
                "enableUspsCass": {
                    "type": "boolean",
                    "description": "Enable USPS CASS validation for US addresses",
                },
            },
            "required": ["apiKey", "address"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (parameters.get("apiKey") or "").strip()
        if self._is_placeholder_token(api_key) or not api_key:
            return ToolResult(success=False, output="", error="Google Maps API key not configured.")

        headers = {
            "Content-Type": "application/json",
        }

        body: Dict[str, Any] = {
            "address": {
                "addressLines": [parameters["address"].strip()],
            },
        }
        region_code = parameters.get("regionCode", "").strip()
        if region_code:
            body["address"]["regionCode"] = region_code
        locality = parameters.get("locality", "").strip()
        if locality:
            body["address"]["locality"] = locality
        if "enableUspsCass" in parameters:
            body["enableUspsCass"] = parameters["enableUspsCass"]

        url = f"https://addressvalidation.googleapis.com/v1:validateAddress?key={api_key}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
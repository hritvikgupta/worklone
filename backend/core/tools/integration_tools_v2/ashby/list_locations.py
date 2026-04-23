from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListLocationsTool(BaseTool):
    name = "ashby_list_locations"
    description = "Lists all locations configured in Ashby."
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
                    "description": "Ashby API Key",
                },
            },
            "required": ["apiKey"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = parameters.get("apiKey")
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Access token not configured.")

        auth_value = base64.b64encode(f"{api_key}:".encode()).decode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_value}",
        }
        url = "https://api.ashbyhq.com/location.list"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={})

                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)

                data = response.json()

                if not data.get("success", False):
                    error_msg = data.get("errorInfo", {}).get("message", "Failed to list locations")
                    return ToolResult(success=False, output="", error=error_msg)

                locations = []
                results = data.get("results", [])
                for l in results:
                    address = None
                    address_obj = l.get("address", {})
                    postal_address = address_obj.get("postalAddress")
                    if postal_address:
                        address = {
                            "city": postal_address.get("addressLocality"),
                            "region": postal_address.get("addressRegion"),
                            "country": postal_address.get("addressCountry"),
                        }
                    loc = {
                        "id": l.get("id"),
                        "name": l.get("name"),
                        "isArchived": l.get("isArchived", False),
                        "isRemote": l.get("isRemote", False),
                        "address": address,
                    }
                    locations.append(loc)

                output_data = {"locations": locations}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
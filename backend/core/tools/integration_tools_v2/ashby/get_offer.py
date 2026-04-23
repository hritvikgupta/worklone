from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyGetOfferTool(BaseTool):
    name = "ashby_get_offer"
    description = "Retrieves full details about a single offer by its ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        if context is None:
            return ""
        return context.get("ASHBY_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "apiKey": {
                    "type": "string",
                    "description": "Ashby API Key",
                },
                "offerId": {
                    "type": "string",
                    "description": "The UUID of the offer to fetch",
                },
            },
            "required": ["apiKey", "offerId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{access_token}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = "https://api.ashbyhq.com/offer.info"
        body = {
            "offerId": parameters.get("offerId"),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if not data.get("success", False):
                        error_msg = data.get("errorInfo", {}).get("message", "Failed to get offer")
                        return ToolResult(success=False, output="", error=error_msg)
                    
                    r = data.get("results", {})
                    v = r.get("latestVersion")
                    
                    output = {
                        "id": r.get("id"),
                        "offerStatus": r.get("offerStatus"),
                        "acceptanceStatus": r.get("acceptanceStatus"),
                        "applicationId": r.get("applicationId"),
                        "startDate": v.get("startDate") if v else None,
                        "salary": None,
                        "openingId": v.get("openingId") if v else None,
                        "createdAt": v.get("createdAt") if v else None,
                    }
                    
                    if v and v.get("salary"):
                        output["salary"] = {
                            "currencyCode": v["salary"].get("currencyCode"),
                            "value": v["salary"].get("value"),
                        }
                    
                    return ToolResult(success=True, output=json.dumps(output, default=str), data=output)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
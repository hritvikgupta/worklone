from typing import Any, Dict
import httpx
import base64
import json
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListOffersTool(BaseTool):
    name = "ashby_list_offers"
    description = "Lists all offers with their latest version in an Ashby organization."
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("ASHBY_API_KEY") if context else None
        if not api_key or self._is_placeholder_token(api_key):
            api_key = os.getenv("ASHBY_API_KEY")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "cursor": {
                    "type": "string",
                    "description": "Opaque pagination cursor from a previous response nextCursor value",
                },
                "perPage": {
                    "type": "number",
                    "description": "Number of results per page",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Ashby API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        body: Dict[str, Any] = {}
        cursor = parameters.get("cursor")
        if cursor:
            body["cursor"] = cursor
        per_page = parameters.get("perPage")
        if per_page is not None:
            body["limit"] = per_page
        
        url = "https://api.ashbyhq.com/offer.list"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    if isinstance(data, dict) and data.get("success"):
                        results = data.get("results", [])
                        offers = []
                        for o in results:
                            v = o.get("latestVersion", {}) if isinstance(o, dict) else {}
                            salary_data = v.get("salary") if isinstance(v, dict) else None
                            salary = None
                            if salary_data and isinstance(salary_data, dict):
                                salary = {
                                    "currencyCode": salary_data.get("currencyCode"),
                                    "value": salary_data.get("value"),
                                }
                            offer = {
                                "id": o.get("id"),
                                "offerStatus": o.get("offerStatus"),
                                "acceptanceStatus": o.get("acceptanceStatus"),
                                "applicationId": o.get("applicationId"),
                                "startDate": v.get("startDate"),
                                "salary": salary,
                                "openingId": v.get("openingId"),
                                "createdAt": v.get("createdAt"),
                            }
                            offers.append(offer)
                        transformed_data = {
                            "offers": offers,
                            "moreDataAvailable": data.get("moreDataAvailable", False),
                            "nextCursor": data.get("nextCursor"),
                        }
                        output_str = json.dumps(transformed_data)
                        return ToolResult(success=True, output=output_str, data=transformed_data)
                    else:
                        error_msg = ""
                        if isinstance(data, dict):
                            error_info = data.get("errorInfo")
                            if isinstance(error_info, dict):
                                error_msg = error_info.get("message", "Failed to list offers")
                        return ToolResult(success=False, output="", error=error_msg)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
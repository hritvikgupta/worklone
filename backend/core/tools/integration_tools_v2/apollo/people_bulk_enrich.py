from typing import Any, Dict, List
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloPeopleBulkEnrichTool(BaseTool):
    name = "apollo_people_bulk_enrich"
    description = "Enrich data for up to 10 people at once using Apollo"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="APOLLO_API_KEY",
                description="Apollo API key",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "people": {
                    "type": "array",
                    "description": "Array of people to enrich (max 10)",
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "additionalProperties": True
                    }
                },
                "reveal_personal_emails": {
                    "type": "boolean",
                    "description": "Reveal personal email addresses (uses credits)"
                },
                "reveal_phone_number": {
                    "type": "boolean",
                    "description": "Reveal phone numbers (uses credits)"
                }
            },
            "required": ["people"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("APOLLO_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }
        
        body = {
            "details": parameters.get("people", [])[:10],
            "reveal_personal_emails": parameters.get("reveal_personal_emails"),
            "reveal_phone_number": parameters.get("reveal_phone_number"),
        }
        
        url = "https://api.apollo.io/api/v1/people/bulk_match"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
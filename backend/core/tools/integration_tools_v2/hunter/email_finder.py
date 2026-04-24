from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HunterEmailFinderTool(BaseTool):
    name = "hunter_email_finder"
    description = "Finds the most likely email address for a person given their name and company domain."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="hunter_api_key",
                description="Hunter.io API Key",
                env_var="HUNTER_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": 'Company domain name (e.g., "stripe.com", "company.io")',
                },
                "first_name": {
                    "type": "string",
                    "description": "Person\'s first name (e.g., \"John\", \"Sarah\")",
                },
                "last_name": {
                    "type": "string",
                    "description": "Person\'s last name (e.g., \"Smith\", \"Johnson\")",
                },
                "company": {
                    "type": "string",
                    "description": 'Company name (e.g., "Stripe", "Acme Inc")',
                },
            },
            "required": ["domain", "first_name", "last_name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("hunter_api_key") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        url = "https://api.hunter.io/v2/email-finder"
        params: Dict[str, str] = {
            "domain": parameters["domain"],
            "first_name": parameters["first_name"],
            "last_name": parameters["last_name"],
            "api_key": api_key,
        }
        if parameters.get("company"):
            params["company"] = parameters["company"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
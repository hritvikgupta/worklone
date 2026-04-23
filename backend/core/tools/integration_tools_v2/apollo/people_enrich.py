from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloPeopleEnrichTool(BaseTool):
    name = "apollo_people_enrich"
    description = "Enrich data for a single person using Apollo"
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

    def _resolve_api_key(self, context: dict | None) -> str:
        return (context or {}).get("APOLLO_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "first_name": {
                    "type": "string",
                    "description": "First name of the person"
                },
                "last_name": {
                    "type": "string",
                    "description": "Last name of the person"
                },
                "email": {
                    "type": "string",
                    "description": "Email address of the person"
                },
                "organization_name": {
                    "type": "string",
                    "description": "Company name where the person works"
                },
                "domain": {
                    "type": "string",
                    "description": 'Company domain (e.g., "apollo.io", "acme.com")'
                },
                "linkedin_url": {
                    "type": "string",
                    "description": "LinkedIn profile URL"
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
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Apollo API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }
        
        url = "https://api.apollo.io/api/v1/people/match"
        
        body: Dict[str, Any] = {}
        string_fields = {
            "first_name",
            "last_name",
            "email",
            "organization_name",
            "domain",
            "linkedin_url"
        }
        bool_fields = {
            "reveal_personal_emails",
            "reveal_phone_number"
        }
        for key, value in parameters.items():
            if key in string_fields and value:
                body[key] = value
            elif key in bool_fields:
                body[key] = value
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
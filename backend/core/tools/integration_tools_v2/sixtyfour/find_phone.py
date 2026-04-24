from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class SixtyfourFindPhoneTool(BaseTool):
    name = "sixtyfour_find_phone"
    description = "Find phone numbers for a lead using Sixtyfour AI."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SIXTYFOUR_API_KEY",
                description="Sixtyfour API key",
                env_var="SIXTYFOUR_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Full name of the person",
                },
                "company": {
                    "type": "string",
                    "description": "Company name",
                },
                "linkedinUrl": {
                    "type": "string",
                    "description": "LinkedIn profile URL",
                },
                "domain": {
                    "type": "string",
                    "description": "Company website domain",
                },
                "email": {
                    "type": "string",
                    "description": "Email address",
                },
            },
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("SIXTYFOUR_API_KEY")

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Access token not configured.")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }

        lead = {
            "name": parameters["name"],
        }
        if parameters.get("company"):
            lead["company"] = parameters["company"]
        if parameters.get("linkedinUrl"):
            lead["linkedin_url"] = parameters["linkedinUrl"]
        if parameters.get("domain"):
            lead["domain"] = parameters["domain"]
        if parameters.get("email"):
            lead["email"] = parameters["email"]

        json_body = {
            "lead": lead,
        }

        url = "https://api.sixtyfour.ai/find-phone"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
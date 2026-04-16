from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class SixtyfourFindEmailTool(BaseTool):
    name = "sixtyfour_find_email"
    description = "Find email addresses for a lead using Sixtyfour AI."
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

    def _build_body(self, parameters: dict) -> dict:
        lead = {"name": parameters["name"]}
        optional_fields = {
            "company": "company",
            "linkedinUrl": "linkedin",
            "domain": "domain",
            "phone": "phone",
            "title": "title",
        }
        for param_key, body_key in optional_fields.items():
            value = parameters.get(param_key)
            if value:
                lead[body_key] = value
        body = {"lead": lead}
        mode = parameters.get("mode")
        if mode:
            body["mode"] = mode
        return body

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
                "phone": {
                    "type": "string",
                    "description": "Phone number",
                },
                "title": {
                    "type": "string",
                    "description": "Job title",
                },
                "mode": {
                    "type": "string",
                    "description": "Email discovery mode: PROFESSIONAL (default) or PERSONAL",
                },
            },
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = (context or {}).get("SIXTYFOUR_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Sixtyfour API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }
        url = "https://api.sixtyfour.ai/find-email"
        body = self._build_body(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_detail = response.text
                    try:
                        err_data = response.json()
                        for key in ["error", "message", "detail"]:
                            if err_data.get(key):
                                error_detail = err_data[key]
                                break
                    except:
                        pass
                    return ToolResult(
                        success=False, output="", error=f"API error ({response.status_code}): {error_detail}"
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
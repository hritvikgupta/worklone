from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HunterEmailCountTool(BaseTool):
    name = "hunter_email_count"
    description = "Returns the total number of email addresses found for a domain or company."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUNTER_API_KEY",
                description="Hunter.io API Key",
                env_var="HUNTER_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> str:
        api_key = (context or {}).get("HUNTER_API_KEY")
        if api_key is None:
            api_key = os.getenv("HUNTER_API_KEY")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": 'Domain to count emails for (e.g., "stripe.com"). Required if company not provided',
                },
                "company": {
                    "type": "string",
                    "description": 'Company name to count emails for (e.g., "Stripe", "Acme Inc"). Required if domain not provided',
                },
                "type": {
                    "type": "string",
                    "description": 'Filter for personal or generic emails only (e.g., "personal", "generic", "all")',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Hunter.io API key not configured.")

        domain = parameters.get("domain")
        company = parameters.get("company")
        if not domain and not company:
            return ToolResult(success=False, output="", error="Either domain or company must be provided")

        type_filter = parameters.get("type")

        headers = {
            "Content-Type": "application/json",
        }

        url = "https://api.hunter.io/v2/email-count"
        params_dict = {
            "api_key": api_key,
        }
        if domain:
            params_dict["domain"] = domain
        if company:
            params_dict["company"] = company
        if type_filter and type_filter != "all":
            params_dict["type"] = type_filter

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
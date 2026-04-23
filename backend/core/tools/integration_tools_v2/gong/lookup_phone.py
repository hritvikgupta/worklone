import os
import base64
from urllib.parse import quote
import httpx
from typing import Any
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GongLookupPhoneTool(BaseTool):
    name = "gong_lookup_phone"
    description = "Find all references to a phone number in Gong (calls, email messages, meetings, CRM data, and associated contacts)."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GONG_ACCESS_KEY",
                description="Gong API Access Key",
                env_var="GONG_ACCESS_KEY",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="GONG_ACCESS_KEY_SECRET",
                description="Gong API Access Key Secret",
                env_var="GONG_ACCESS_KEY_SECRET",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "phoneNumber": {
                    "type": "string",
                    "description": "Phone number to look up (must start with + followed by country code)",
                },
            },
            "required": ["phoneNumber"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_key = context.get("GONG_ACCESS_KEY") if context else None
        access_key_secret = context.get("GONG_ACCESS_KEY_SECRET") if context else None
        if not access_key:
            access_key = os.getenv("GONG_ACCESS_KEY")
        if not access_key_secret:
            access_key_secret = os.getenv("GONG_ACCESS_KEY_SECRET")

        if self._is_placeholder_token(access_key or "") or self._is_placeholder_token(access_key_secret or ""):
            return ToolResult(success=False, output="", error="Gong access keys not configured.")

        phone_number = parameters["phoneNumber"]
        url = f"https://api.gong.io/v2/data-privacy/data-for-phone-number?phoneNumber={quote(phone_number)}"

        auth_string = f"{access_key}:{access_key_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
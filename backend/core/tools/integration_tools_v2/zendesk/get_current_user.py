from typing import Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskGetCurrentUserTool(BaseTool):
    name = "zendesk_get_current_user"
    description = "Get the currently authenticated user from Zendesk"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="zendesk_email",
                description="Your Zendesk email address",
                env_var="ZENDESK_EMAIL",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="zendesk_api_token",
                description="Zendesk API token",
                env_var="ZENDESK_API_TOKEN",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="zendesk_subdomain",
                description="Your Zendesk subdomain",
                env_var="ZENDESK_SUBDOMAIN",
                required=True,
                auth_type="api_key",
            ),
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Your Zendesk email address",
                },
                "apiToken": {
                    "type": "string",
                    "description": "Zendesk API token",
                },
                "subdomain": {
                    "type": "string",
                    "description": "Your Zendesk subdomain",
                },
            },
            "required": ["email", "apiToken", "subdomain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        creds = context or {}
        email = creds.get("zendesk_email") or creds.get("email") or parameters.get("email")
        api_token = creds.get("zendesk_api_token") or creds.get("apiToken") or parameters.get("apiToken")
        subdomain = creds.get("zendesk_subdomain") or creds.get("subdomain") or parameters.get("subdomain")

        if not all([email, api_token, subdomain]) or \
           self._is_placeholder_token(email) or \
           self._is_placeholder_token(api_token) or \
           self._is_placeholder_token(subdomain):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        url = f"https://{subdomain}.zendesk.com/api/v2/users/me"

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode()).decode()

        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
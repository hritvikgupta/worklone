from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskDeleteUserTool(BaseTool):
    name = "zendesk_delete_user"
    description = "Delete a user from Zendesk"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="email",
                description="Your Zendesk email address",
                env_var="ZENDESK_EMAIL",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="api_token",
                description="Zendesk API token",
                env_var="ZENDESK_API_TOKEN",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="subdomain",
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
                "userId": {
                    "type": "string",
                    "description": "User ID to delete as a numeric string (e.g., \"12345\")",
                },
            },
            "required": ["email", "apiToken", "subdomain", "userId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        credentials = context.get("credentials", {}) if context else {}
        email = credentials.get("email") or parameters.get("email")
        api_token = credentials.get("api_token") or parameters.get("apiToken")
        subdomain = credentials.get("subdomain") or parameters.get("subdomain")
        user_id = parameters.get("userId")

        if not all([email, api_token, subdomain, user_id]):
            return ToolResult(success=False, output="", error="Missing required parameters or credentials.")

        if (
            self._is_placeholder_token(email)
            or self._is_placeholder_token(api_token)
            or self._is_placeholder_token(subdomain)
        ):
            return ToolResult(success=False, output="", error="Access token not configured.")

        url = f"https://{subdomain}.zendesk.com/api/v2/users/{user_id}"

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = {
                        "deleted": True,
                        "user_id": user_id,
                        "success": True,
                    }
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
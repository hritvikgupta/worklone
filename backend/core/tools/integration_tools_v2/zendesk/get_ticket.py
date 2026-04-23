from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskGetTicketTool(BaseTool):
    name = "zendesk_get_ticket"
    description = "Get a single ticket by ID from Zendesk"
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
                "ticketId": {
                    "type": "string",
                    "description": 'Ticket ID to retrieve as a numeric string (e.g., "12345")',
                },
            },
            "required": ["email", "apiToken", "subdomain", "ticketId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("zendesk_email") if context else None
        api_token = context.get("zendesk_api_token") if context else None
        subdomain = context.get("zendesk_subdomain") if context else None
        ticket_id = parameters.get("ticketId")

        if not all([email, api_token, subdomain, ticket_id]):
            return ToolResult(
                success=False,
                output="",
                error="Missing required credentials or ticketId.",
            )

        if self._is_placeholder_token(api_token):
            return ToolResult(
                success=False,
                output="",
                error="Zendesk API token not configured.",
            )

        credentials_str = f"{email}/token:{api_token}"
        b64_credentials = base64.b64encode(credentials_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {b64_credentials}",
            "Content-Type": "application/json",
        }

        url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output=response.text,
                        data=response.json(),
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=response.text,
                    )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"API error: {str(e)}",
            )
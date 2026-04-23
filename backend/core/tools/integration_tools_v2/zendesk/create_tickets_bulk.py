from typing import Any, Dict, Tuple
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZendeskCreateTicketsBulkTool(BaseTool):
    name = "zendesk_create_tickets_bulk"
    description = "Create multiple tickets in Zendesk at once (max 100)"
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

    async def _resolve_token(self, context: dict | None, context_keys: Tuple[str, ...], env_keys: Tuple[str, ...]) -> str:
        connection = await resolve_oauth_connection(
            "zendesk",
            context=context,
            context_token_keys=context_keys,
            env_token_keys=env_keys,
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tickets": {
                    "type": "string",
                    "description": 'JSON array of ticket objects to create (max 100). Each ticket should have subject and comment properties (e.g., [{"subject": "Issue 1", "comment": {"body": "Description"}}])',
                },
            },
            "required": ["tickets"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = await self._resolve_token(context, ("zendesk_email",), ("ZENDESK_EMAIL",))
        api_token = await self._resolve_token(context, ("zendesk_api_token",), ("ZENDESK_API_TOKEN",))
        subdomain = await self._resolve_token(context, ("zendesk_subdomain",), ("ZENDESK_SUBDOMAIN",))

        if (
            self._is_placeholder_token(email)
            or self._is_placeholder_token(api_token)
            or self._is_placeholder_token(subdomain)
        ):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        try:
            tickets = json.loads(parameters["tickets"])
            if not isinstance(tickets, list):
                raise ValueError("Tickets must be a list")
            if len(tickets) > 100:
                raise ValueError("Max 100 tickets allowed")
        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="Invalid tickets JSON format")
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }
        url = f"https://{subdomain}.zendesk.com/api/v2/tickets/create_many.json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={"tickets": tickets})

                if response.status_code in [200, 201]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
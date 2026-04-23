from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZendeskCreateUsersBulkTool(BaseTool):
    name = "zendesk_create_users_bulk"
    description = "Create multiple users in Zendesk using bulk import"
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
        ]

    async def _resolve_email(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "zendesk",
            context=context,
            context_token_keys=("zendesk_email",),
            env_token_keys=("ZENDESK_EMAIL",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    async def _resolve_api_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "zendesk",
            context=context,
            context_token_keys=("zendesk_api_token",),
            env_token_keys=("ZENDESK_API_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subdomain": {
                    "type": "string",
                    "description": "Your Zendesk subdomain",
                },
                "users": {
                    "type": "string",
                    "description": 'JSON array of user objects to create (e.g., [{"name": "User1", "email": "user1@example.com"}])',
                },
            },
            "required": ["subdomain", "users"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = await self._resolve_email(context)
        api_token = await self._resolve_api_token(context)

        if self._is_placeholder_token(email) or self._is_placeholder_token(api_token):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        credentials = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        subdomain = parameters["subdomain"]
        users_str = parameters["users"]

        try:
            users = json.loads(users_str)
        except json.JSONDecodeError:
            return ToolResult(success=False, output="", error="Invalid users JSON format")

        body = {"users": users}
        url = f"https://{subdomain}.zendesk.com/api/v2/users/create_many"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
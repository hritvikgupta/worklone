from typing import Any, Dict, Tuple
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZendeskGetOrganizationTool(BaseTool):
    name = "zendesk_get_organization"
    description = "Get a single organization by ID from Zendesk"
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

    async def _resolve_token(self, context: dict | None, context_token_keys: Tuple[str, ...], env_token_keys: Tuple[str, ...]) -> str:
        connection = await resolve_oauth_connection(
            "zendesk",
            context=context,
            context_token_keys=context_token_keys,
            env_token_keys=env_token_keys,
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    async def _resolve_zendesk_credentials(self, context: dict | None) -> Tuple[str, str, str]:
        email = await self._resolve_token(context, ("email", "zendesk_email"), ("ZENDESK_EMAIL",))
        api_token = await self._resolve_token(context, ("apiToken", "zendesk_api_token"), ("ZENDESK_API_TOKEN",))
        subdomain = await self._resolve_token(context, ("subdomain", "zendesk_subdomain"), ("ZENDESK_SUBDOMAIN",))
        return email, api_token, subdomain

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "organizationId": {
                    "type": "string",
                    "description": "Organization ID to retrieve as a numeric string (e.g., \"12345\")",
                },
            },
            "required": ["organizationId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            email, api_token, subdomain = await self._resolve_zendesk_credentials(context)
        except Exception:
            return ToolResult(success=False, output="", error="Failed to resolve Zendesk credentials.")

        if self._is_placeholder_token(email) or self._is_placeholder_token(api_token) or self._is_placeholder_token(subdomain):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        organization_id = parameters.get("organizationId")
        if not organization_id:
            return ToolResult(success=False, output="", error="organizationId is required.")

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        url = f"https://{subdomain}.zendesk.com/api/v2/organizations/{organization_id}.json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
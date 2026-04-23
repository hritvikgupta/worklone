from typing import Any, Dict
import httpx
import base64
import os
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskAutocompleteOrganizationsTool(BaseTool):
    name = "zendesk_autocomplete_organizations"
    description = "Autocomplete organizations in Zendesk by name prefix (for name matching/autocomplete)"
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

    def _get_from_context_or_env(self, context: dict | None, ctx_key: str, env_key: str) -> str | None:
        value = context.get(ctx_key) if context else None
        if value is None:
            value = os.environ.get(env_key)
        if self._is_placeholder_token(value or ""):
            return None
        return value

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Organization name prefix to search for (e.g., \"Acme\")",
                },
                "perPage": {
                    "type": "string",
                    "description": "Results per page as a number string (default: \"100\", max: \"100\")",
                },
                "page": {
                    "type": "string",
                    "description": "Page number for pagination (1-based)",
                },
            },
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = self._get_from_context_or_env(context, "zendesk_email", "ZENDESK_EMAIL")
        api_token = self._get_from_context_or_env(context, "zendesk_api_token", "ZENDESK_API_TOKEN")
        subdomain = self._get_from_context_or_env(context, "zendesk_subdomain", "ZENDESK_SUBDOMAIN")

        if not all([email, api_token, subdomain]):
            return ToolResult(success=False, output="", error="Zendesk credentials (email, API token, subdomain) not configured.")

        credentials_str = f"{email}/token:{api_token}"
        basic_auth = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/json",
        }

        query_params = {
            "name": parameters["name"],
        }
        per_page = parameters.get("perPage")
        if per_page:
            query_params["per_page"] = per_page
        page = parameters.get("page")
        if page:
            query_params["page"] = page

        query_string = urlencode(query_params)
        url = f"https://{subdomain}.zendesk.com/api/v2/organizations/autocomplete?{query_string}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
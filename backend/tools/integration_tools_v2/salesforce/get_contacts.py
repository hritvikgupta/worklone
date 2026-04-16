from typing import Any, Dict
import httpx
from urllib.parse import quote
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class SalesforceGetContactsTool(BaseTool):
    name = "salesforce_get_contacts"
    description = "Get contact(s) from Salesforce - single contact if ID provided, or list if not"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Salesforce access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_credentials(self, context: dict | None) -> tuple[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token, getattr(connection, "instance_url", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "contactId": {
                    "type": "string",
                    "description": "Salesforce Contact ID (18-character string starting with 003) to get a single contact",
                },
                "limit": {
                    "type": "string",
                    "description": "Maximum number of results (default: 100, max: 2000). Only for list query.",
                },
                "fields": {
                    "type": "string",
                    "description": 'Comma-separated field API names (e.g., "Id,FirstName,LastName,Email,Phone")',
                },
                "orderBy": {
                    "type": "string",
                    "description": 'Field and direction for sorting (e.g., "LastName ASC"). Only for list query.',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token, instance_url = await self._resolve_credentials(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        if not instance_url:
            return ToolResult(success=False, output="", error="Instance URL not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        base_url = instance_url.rstrip("/")
        contact_id = parameters.get("contactId")
        if contact_id:
            fields = parameters.get("fields", "Id,FirstName,LastName,Email,Phone,AccountId,Title,Department")
            url = f"{base_url}/services/data/v59.0/sobjects/Contact/{contact_id}?fields={fields}"
        else:
            limit_str = parameters.get("limit", "")
            limit = int(limit_str) if limit_str else 100
            fields = parameters.get("fields", "Id,FirstName,LastName,Email,Phone,AccountId,Title,Department")
            order_by = parameters.get("orderBy", "LastName ASC")
            query = f"SELECT {fields} FROM Contact ORDER BY {order_by} LIMIT {limit}"
            encoded_query = quote(query)
            url = f"{base_url}/services/data/v59.0/query?q={encoded_query}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())

                try:
                    err_data = response.json()
                    if isinstance(err_data, list) and err_data:
                        error_msg = err_data[0].get("message", "Failed to fetch contacts from Salesforce")
                    elif isinstance(err_data, dict):
                        error_msg = err_data.get("message", "Failed to fetch contacts from Salesforce")
                    else:
                        error_msg = response.text
                except Exception:
                    error_msg = response.text

                return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
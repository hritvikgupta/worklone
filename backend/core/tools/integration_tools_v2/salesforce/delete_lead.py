from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceDeleteLeadTool(BaseTool):
    name = "salesforce_delete_lead"
    description = "Delete a lead"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="accessToken",
                description="Access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            ),
            CredentialRequirement(
                key="idToken",
                description="ID token (used to derive instance URL)",
                env_var="SALESFORCE_ID_TOKEN",
                required=False,
                auth_type="oauth",
            ),
            CredentialRequirement(
                key="instanceUrl",
                description="Salesforce instance URL (e.g., https://your-domain.my.salesforce.com)",
                env_var="SALESFORCE_INSTANCE_URL",
                required=False,
                auth_type="oauth",
            ),
        ]

    async def _resolve_connection(self, context: dict | None) -> Any:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken", "idToken", "instanceUrl"),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN", "SALESFORCE_ID_TOKEN", "SALESFORCE_INSTANCE_URL"),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "leadId": {
                    "type": "string",
                    "description": "Salesforce Lead ID to delete (18-character string starting with 00Q)",
                },
            },
            "required": ["leadId"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = getattr(connection, "instance_url", None)

        if not instance_url:
            return ToolResult(success=False, output="", error="Instance URL not available.")

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        lead_id = parameters["leadId"]
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Lead/{lead_id}"

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 204]:
                    data = {"id": lead_id, "deleted": True}
                    return ToolResult(success=True, output="Lead deleted successfully.", data=data)
                else:
                    try:
                        err_data = response.json()
                    except:
                        err_data = {}
                    if isinstance(err_data, list) and err_data:
                        message = err_data[0].get("message", str(err_data[0]))
                    elif isinstance(err_data, dict):
                        message = err_data.get("message", response.text)
                    else:
                        message = response.text
                    return ToolResult(success=False, output="", error=message)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
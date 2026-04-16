from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceDeleteContactTool(BaseTool):
    name = "salesforce_delete_contact"
    description = "Delete a contact from Salesforce CRM"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Access token for Salesforce",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_connection(self, context: dict | None) -> Any:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("salesforce_token",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "contactId": {
                    "type": "string",
                    "description": "Salesforce Contact ID to delete (18-character string starting with 003)",
                },
            },
            "required": ["contactId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = getattr(connection, "instance_url", None)
        
        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Salesforce access token or instance URL not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        contact_id = parameters.get("contactId")
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Contact/{contact_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(
                        success=True,
                        output="",
                        data={"id": contact_id or "", "deleted": True},
                    )
                else:
                    try:
                        error_data = response.json()
                        if isinstance(error_data, list) and error_data:
                            error_msg = error_data[0].get("message", str(error_data[0]))
                        else:
                            error_msg = error_data.get("message", response.text) if error_data else response.text
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceUpdateContactTool(BaseTool):
    name = "salesforce_update_contact"
    description = "Update an existing contact in Salesforce CRM"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SALESFORCE_ACCESS_TOKEN",
                description="Access token",
                env_var="SALESFORCE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_connection(self, context: dict | None) -> Dict[str, str]:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return {
            "access_token": connection.access_token,
            "instance_url": getattr(connection, "instance_url", None),
        }

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "contactId": {
                    "type": "string",
                    "description": "Salesforce Contact ID to update (18-character string starting with 003)",
                },
                "lastName": {
                    "type": "string",
                    "description": "Last name",
                },
                "firstName": {
                    "type": "string",
                    "description": "First name",
                },
                "email": {
                    "type": "string",
                    "description": "Email address",
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number",
                },
                "accountId": {
                    "type": "string",
                    "description": "Salesforce Account ID (18-character string starting with 001)",
                },
                "title": {
                    "type": "string",
                    "description": "Job title",
                },
                "department": {
                    "type": "string",
                    "description": "Department",
                },
                "mailingStreet": {
                    "type": "string",
                    "description": "Mailing street",
                },
                "mailingCity": {
                    "type": "string",
                    "description": "Mailing city",
                },
                "mailingState": {
                    "type": "string",
                    "description": "Mailing state",
                },
                "mailingPostalCode": {
                    "type": "string",
                    "description": "Mailing postal code",
                },
                "mailingCountry": {
                    "type": "string",
                    "description": "Mailing country",
                },
                "description": {
                    "type": "string",
                    "description": "Contact description",
                },
            },
            "required": ["contactId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection_dict = await self._resolve_connection(context)
        access_token = connection_dict["access_token"]
        instance_url = connection_dict["instance_url"]

        if self._is_placeholder_token(access_token) or not instance_url:
            return ToolResult(success=False, output="", error="Salesforce access token or instance URL not configured.")

        contact_id = parameters["contactId"]
        url = f"{instance_url.rstrip('/')}/services/data/v59.0/sobjects/Contact/{contact_id}"

        field_map = {
            "lastName": "LastName",
            "firstName": "FirstName",
            "email": "Email",
            "phone": "Phone",
            "accountId": "AccountId",
            "title": "Title",
            "department": "Department",
            "mailingStreet": "MailingStreet",
            "mailingCity": "MailingCity",
            "mailingState": "MailingState",
            "mailingPostalCode": "MailingPostalCode",
            "mailingCountry": "MailingCountry",
            "description": "Description",
        }
        body: Dict[str, Any] = {}
        for param_key, sf_key in field_map.items():
            if param_key in parameters and parameters[param_key]:
                body[sf_key] = parameters[param_key]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    data = None
                    try:
                        data = response.json()
                    except:
                        data = {"id": contact_id, "updated": True}
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        if isinstance(err_data, list) and err_data:
                            error_msg = err_data[0].get("message", error_msg)
                        elif isinstance(err_data, dict):
                            error_msg = err_data.get("message", error_msg)
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
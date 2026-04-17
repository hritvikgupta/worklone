from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SalesforceCreateContactTool(BaseTool):
    name = "salesforce_create_contact"
    description = "Create a new contact in Salesforce CRM"
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

    async def _resolve_connection(self, context: dict | None) -> Any:
        connection = await resolve_oauth_connection(
            "salesforce",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("SALESFORCE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "lastName": {
                    "type": "string",
                    "description": "Last name (required)",
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
            "required": ["lastName"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        connection = await self._resolve_connection(context)
        access_token = connection.access_token
        instance_url = getattr(connection, "instance_url", None)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        if not instance_url:
            return ToolResult(success=False, output="", error="Instance URL not available.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        field_mapping = {
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
        body = {}
        for param_name, sf_field in field_mapping.items():
            value = parameters.get(param_name)
            if value:
                body[sf_field] = value
        
        url = f"{instance_url}/services/data/v59.0/sobjects/Contact"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
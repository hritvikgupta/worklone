from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomCreateContactTool(BaseTool):
    name = "create_contact_in_intercom"
    description = "Create a new contact in Intercom with email, external_id, or role. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INTERCOM_ACCESS_TOKEN",
                description="Intercom API access token",
                env_var="INTERCOM_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "intercom",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "The role of the contact. Accepts 'user' or 'lead'. Defaults to 'lead' if not specified.",
                },
                "email": {
                    "type": "string",
                    "description": "The contact's email address",
                },
                "external_id": {
                    "type": "string",
                    "description": "A unique identifier for the contact provided by the client",
                },
                "phone": {
                    "type": "string",
                    "description": "The contact's phone number",
                },
                "name": {
                    "type": "string",
                    "description": "The contact's name",
                },
                "avatar": {
                    "type": "string",
                    "description": "An avatar image URL for the contact",
                },
                "signed_up_at": {
                    "type": "number",
                    "description": "The time the user signed up as a Unix timestamp",
                },
                "last_seen_at": {
                    "type": "number",
                    "description": "The time the user was last seen as a Unix timestamp",
                },
                "owner_id": {
                    "type": "string",
                    "description": "The id of an admin that has been assigned account ownership of the contact",
                },
                "unsubscribed_from_emails": {
                    "type": "boolean",
                    "description": "Whether the contact is unsubscribed from emails",
                },
                "custom_attributes": {
                    "type": "string",
                    "description": "Custom attributes as JSON object (e.g., {\"attribute_name\": \"value\"})",
                },
                "company_id": {
                    "type": "string",
                    "description": "Company ID to associate the contact with during creation",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        body: dict[str, Any] = {}
        simple_fields = [
            "role",
            "email",
            "external_id",
            "phone",
            "name",
            "avatar",
            "signed_up_at",
            "last_seen_at",
            "owner_id",
            "company_id",
        ]
        for field in simple_fields:
            if field in parameters:
                body[field] = parameters[field]
        if "unsubscribed_from_emails" in parameters:
            body["unsubscribed_from_emails"] = parameters["unsubscribed_from_emails"]
        if "custom_attributes" in parameters and parameters["custom_attributes"]:
            try:
                body["custom_attributes"] = json.loads(parameters["custom_attributes"])
            except json.JSONDecodeError:
                pass
        
        url = "https://api.intercom.io/contacts"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskCreateUserTool(BaseTool):
    name = "zendesk_create_user"
    description = "Create a new user in Zendesk"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "User full name (e.g., \"John Smith\")",
                },
                "userEmail": {
                    "type": "string",
                    "description": "User email address (e.g., \"john@example.com\")",
                },
                "role": {
                    "type": "string",
                    "description": 'User role: "end-user", "agent", or "admin"',
                },
                "phone": {
                    "type": "string",
                    "description": "User phone number (e.g., \"+1-555-123-4567\")",
                },
                "organizationId": {
                    "type": "string",
                    "description": 'Organization ID as a numeric string (e.g., "12345")',
                },
                "verified": {
                    "type": "string",
                    "description": 'Set to "true" to skip email verification, or "false" otherwise',
                },
                "tags": {
                    "type": "string",
                    "description": 'Comma-separated tags (e.g., "vip, enterprise")',
                },
                "customFields": {
                    "type": "string",
                    "description": 'Custom fields as JSON object (e.g., {"field_id": "value"})',
                },
            },
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("zendesk_email") if context else None
        api_token = context.get("zendesk_api_token") if context else None
        subdomain = context.get("zendesk_subdomain") if context else None

        if not all([email, api_token, subdomain]):
            return ToolResult(success=False, output="", error="Missing credentials.")

        if any(self._is_placeholder_token(v) for v in [email, api_token, subdomain]):
            return ToolResult(success=False, output="", error="Access credentials not configured.")

        credentials_str = f"{email}/token:{api_token}"
        b64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {b64_credentials}",
            "Content-Type": "application/json",
        }

        url = f"https://{subdomain}.zendesk.com/api/v2/users"

        user: Dict[str, Any] = {}
        name = parameters.get("name")
        if name:
            user["name"] = name
        user_email_param = parameters.get("userEmail")
        if user_email_param:
            user["email"] = user_email_param
        role = parameters.get("role")
        if role:
            user["role"] = role
        phone = parameters.get("phone")
        if phone:
            user["phone"] = phone
        organization_id = parameters.get("organizationId")
        if organization_id:
            user["organization_id"] = organization_id
        verified = parameters.get("verified")
        if verified:
            user["verified"] = verified.lower() == "true"
        tags_str = parameters.get("tags")
        if tags_str:
            user["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]
        custom_fields_str = parameters.get("customFields")
        if custom_fields_str:
            try:
                user["user_fields"] = json.loads(custom_fields_str)
            except json.JSONDecodeError:
                pass

        body = {"user": user}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
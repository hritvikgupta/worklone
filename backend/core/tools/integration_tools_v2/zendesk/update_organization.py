from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskUpdateOrganizationTool(BaseTool):
    name = "zendesk_update_organization"
    description = "Update an existing organization in Zendesk"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Your Zendesk email address",
                },
                "apiToken": {
                    "type": "string",
                    "description": "Zendesk API token",
                },
                "subdomain": {
                    "type": "string",
                    "description": "Your Zendesk subdomain",
                },
                "organizationId": {
                    "type": "string",
                    "description": 'Organization ID to update as a numeric string (e.g., "12345")',
                },
                "name": {
                    "type": "string",
                    "description": 'New organization name (e.g., "Acme Corporation")',
                },
                "domainNames": {
                    "type": "string",
                    "description": 'Comma-separated domain names (e.g., "acme.com, acme.org")',
                },
                "details": {
                    "type": "string",
                    "description": "Organization details text",
                },
                "notes": {
                    "type": "string",
                    "description": "Organization notes text",
                },
                "tags": {
                    "type": "string",
                    "description": 'Comma-separated tags (e.g., "enterprise, priority")',
                },
                "customFields": {
                    "type": "string",
                    "description": 'Custom fields as JSON object (e.g., {\"field_id\": \"value\"})',
                },
            },
            "required": ["email", "apiToken", "subdomain", "organizationId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("zendesk_email") if context else None
        api_token = context.get("zendesk_api_token") if context else None

        if self._is_placeholder_token(email or "") or self._is_placeholder_token(api_token or ""):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        subdomain = parameters["subdomain"]
        organization_id = parameters["organizationId"]

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        url = f"https://{subdomain}.zendesk.com/api/v2/organizations/{organization_id}"

        organization: dict[str, Any] = {}
        name = parameters.get("name")
        if name:
            organization["name"] = name
        domain_names_str = parameters.get("domainNames")
        if domain_names_str:
            organization["domain_names"] = [d.strip() for d in domain_names_str.split(",")]
        details = parameters.get("details")
        if details:
            organization["details"] = details
        notes = parameters.get("notes")
        if notes:
            organization["notes"] = notes
        tags_str = parameters.get("tags")
        if tags_str:
            organization["tags"] = [t.strip() for t in tags_str.split(",")]
        custom_fields_str = parameters.get("customFields")
        if custom_fields_str:
            try:
                custom_fields = json.loads(custom_fields_str)
                organization["organization_fields"] = custom_fields
            except json.JSONDecodeError:
                pass

        body = {"organization": organization}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
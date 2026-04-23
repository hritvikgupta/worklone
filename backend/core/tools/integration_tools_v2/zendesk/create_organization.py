from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskCreateOrganizationTool(BaseTool):
    name = "zendesk_create_organization"
    description = "Create a new organization in Zendesk"
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
                key="zendesk_subdomain",
                description="Your Zendesk subdomain",
                env_var="ZENDESK_SUBDOMAIN",
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

    def _get_credential(self, context: dict | None, parameters: dict, cred_key: str, param_key: str) -> tuple[str | None, str | None]:
        value = None
        if context:
            value = context.get(cred_key)
        if value is None:
            value = parameters.get(param_key)
        if not value or self._is_placeholder_token(str(value)):
            cred_desc = cred_key.replace("zendesk_", "").replace("_", " ").title()
            return None, f"{cred_desc} not configured."
        return str(value), None

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
                "name": {
                    "type": "string",
                    "description": "Organization name (e.g., \"Acme Corporation\")",
                },
                "domainNames": {
                    "type": "string",
                    "description": "Comma-separated domain names (e.g., \"acme.com, acme.org\")",
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
                    "description": "Comma-separated tags (e.g., \"enterprise, priority\")",
                },
                "customFields": {
                    "type": "string",
                    "description": "Custom fields as JSON object (e.g., {\"field_id\": \"value\"})",
                },
            },
            "required": ["email", "apiToken", "subdomain", "name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email, err = self._get_credential(context, parameters, "zendesk_email", "email")
        if err:
            return ToolResult(success=False, output="", error=err)

        subdomain, err = self._get_credential(context, parameters, "zendesk_subdomain", "subdomain")
        if err:
            return ToolResult(success=False, output="", error=err)

        api_token, err = self._get_credential(context, parameters, "zendesk_api_token", "apiToken")
        if err:
            return ToolResult(success=False, output="", error=err)

        url = f"https://{subdomain}.zendesk.com/api/v2/organizations"

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        body_dict: dict = {"organization": {"name": parameters["name"]}}

        domain_names_str = parameters.get("domainNames")
        if domain_names_str:
            body_dict["organization"]["domain_names"] = [d.strip() for d in domain_names_str.split(",") if d.strip()]

        details = parameters.get("details")
        if details:
            body_dict["organization"]["details"] = details

        notes = parameters.get("notes")
        if notes:
            body_dict["organization"]["notes"] = notes

        tags_str = parameters.get("tags")
        if tags_str:
            body_dict["organization"]["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

        custom_fields_str = parameters.get("customFields")
        if custom_fields_str:
            try:
                custom_fields = json.loads(custom_fields_str)
                body_dict["organization"]["organization_fields"] = custom_fields
            except json.JSONDecodeError:
                return ToolResult(success=False, output="", error="Failed to parse customFields as JSON.")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body_dict)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
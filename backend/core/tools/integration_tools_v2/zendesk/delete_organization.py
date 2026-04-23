from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskDeleteOrganizationTool(BaseTool):
    name = "zendesk_delete_organization"
    description = "Delete an organization from Zendesk"
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
                "subdomain": {
                    "type": "string",
                    "description": "Your Zendesk subdomain",
                },
                "organizationId": {
                    "type": "string",
                    "description": "Organization ID to delete as a numeric string (e.g., \"12345\")",
                },
            },
            "required": ["subdomain", "organizationId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("zendesk_email") if context else None
        api_token = context.get("zendesk_api_token") if context else None

        if self._is_placeholder_token(email) or self._is_placeholder_token(api_token):
            return ToolResult(success=False, output="", error="Zendesk email or API token not configured.")

        subdomain = parameters.get("subdomain")
        organization_id = parameters.get("organizationId")

        if not subdomain or not organization_id:
            return ToolResult(success=False, output="", error="Missing required parameters: subdomain or organizationId.")

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        url = f"https://{subdomain}.zendesk.com/api/v2/organizations/{organization_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except:
                        data = {
                            "deleted": True,
                            "organization_id": organization_id,
                            "success": True,
                        }
                    return ToolResult(success=True, output=response.text, data=data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", str(error_data))
                    except:
                        error_msg = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Zendesk API error ({response.status_code}): {error_msg}",
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
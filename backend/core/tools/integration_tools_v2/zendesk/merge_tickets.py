from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskMergeTicketsTool(BaseTool):
    name = "zendesk_merge_tickets"
    description = "Merge multiple tickets into a target ticket"
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
                "targetTicketId": {
                    "type": "string",
                    "description": "Target ticket ID as a numeric string (tickets will be merged into this one, e.g., \"12345\")",
                },
                "sourceTicketIds": {
                    "type": "string",
                    "description": "Comma-separated source ticket IDs to merge (e.g., \"111, 222, 333\")",
                },
                "targetComment": {
                    "type": "string",
                    "description": "Comment text to add to target ticket after merge",
                },
            },
            "required": ["targetTicketId", "sourceTicketIds"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        if not context:
            return ToolResult(success=False, output="", error="No context provided.")

        email = context.get("zendesk_email")
        api_token = context.get("zendesk_api_token")
        subdomain = context.get("zendesk_subdomain")

        if (
            self._is_placeholder_token(email)
            or self._is_placeholder_token(api_token)
            or self._is_placeholder_token(subdomain)
        ):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        target_ticket_id = parameters["targetTicketId"]
        source_ticket_ids = parameters["sourceTicketIds"]
        target_comment = parameters.get("targetComment")

        url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{target_ticket_id}/merge"

        ids = [id_str.strip() for id_str in source_ticket_ids.split(",")]

        body: Dict[str, Any] = {"ids": ids}
        if target_comment:
            body["target_comment"] = {
                "body": target_comment,
                "public": True,
            }

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 202, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
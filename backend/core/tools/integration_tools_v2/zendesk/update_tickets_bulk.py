from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskUpdateTicketsBulkTool(BaseTool):
    name = "zendesk_update_tickets_bulk"
    description = "Update multiple tickets in Zendesk at once (max 100)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _is_missing_credentials(self, email: str | None, api_token: str | None, subdomain: str | None) -> bool:
        return (
            not email or self._is_placeholder_token(email) or
            not api_token or self._is_placeholder_token(api_token) or
            not subdomain or self._is_placeholder_token(subdomain)
        )

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
                "ticketIds": {
                    "type": "string",
                    "description": "Comma-separated ticket IDs to update (max 100, e.g., \"111, 222, 333\")",
                },
                "status": {
                    "type": "string",
                    "description": "New status for all tickets: \"new\", \"open\", \"pending\", \"hold\", \"solved\", or \"closed\"",
                },
                "priority": {
                    "type": "string",
                    "description": "New priority for all tickets: \"low\", \"normal\", \"high\", or \"urgent\"",
                },
                "assigneeId": {
                    "type": "string",
                    "description": "New assignee ID for all tickets as a numeric string (e.g., \"12345\")",
                },
                "groupId": {
                    "type": "string",
                    "description": "New group ID for all tickets as a numeric string (e.g., \"67890\")",
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tags to add to all tickets (e.g., \"bulk-update, processed\")",
                },
            },
            "required": ["ticketIds"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("zendesk_email") if context else None
        api_token = context.get("zendesk_api_token") if context else None
        subdomain = context.get("zendesk_subdomain") if context else None

        if self._is_missing_credentials(email, api_token, subdomain):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        ticket_ids_str = parameters.get("ticketIds", "").strip()
        if not ticket_ids_str:
            return ToolResult(success=False, output="", error="ticketIds is required.")

        ids = [id.strip() for id in ticket_ids_str.split(",") if id.strip()]
        if len(ids) > 100:
            return ToolResult(success=False, output="", error="Maximum 100 ticket IDs allowed.")

        query_ids = ",".join(ids)
        url = f"https://{subdomain}.zendesk.com/api/v2/tickets/update_many?ids={query_ids}"

        ticket: Dict[str, Any] = {}
        status = parameters.get("status")
        if status:
            ticket["status"] = status
        priority = parameters.get("priority")
        if priority:
            ticket["priority"] = priority
        assignee_id = parameters.get("assigneeId")
        if assignee_id:
            ticket["assignee_id"] = assignee_id
        group_id = parameters.get("groupId")
        if group_id:
            ticket["group_id"] = group_id
        tags_str = parameters.get("tags", "").strip()
        if tags_str:
            ticket["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

        body = {"ticket": ticket}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
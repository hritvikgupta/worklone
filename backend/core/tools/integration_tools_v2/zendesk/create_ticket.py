from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskCreateTicketTool(BaseTool):
    name = "zendesk_create_ticket"
    description = "Create a new ticket in Zendesk with support for custom fields"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="email",
                description="Your Zendesk email address",
                env_var="ZENDESK_EMAIL",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="apiToken",
                description="Zendesk API token",
                env_var="ZENDESK_API_TOKEN",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="subdomain",
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
                "email": {
                    "type": "string",
                    "description": "Your Zendesk email address"
                },
                "apiToken": {
                    "type": "string",
                    "description": "Zendesk API token"
                },
                "subdomain": {
                    "type": "string",
                    "description": "Your Zendesk subdomain"
                },
                "subject": {
                    "type": "string",
                    "description": "Ticket subject (optional - will be auto-generated if not provided)"
                },
                "description": {
                    "type": "string",
                    "description": "Ticket description text (first comment)"
                },
                "priority": {
                    "type": "string",
                    "description": 'Priority: "low", "normal", "high", or "urgent"'
                },
                "status": {
                    "type": "string",
                    "description": 'Status: "new", "open", "pending", "hold", "solved", or "closed"'
                },
                "type": {
                    "type": "string",
                    "description": 'Type: "problem", "incident", "question", or "task"'
                },
                "tags": {
                    "type": "string",
                    "description": 'Comma-separated tags (e.g., "billing, urgent")'
                },
                "assigneeId": {
                    "type": "string",
                    "description": 'Assignee user ID as a numeric string (e.g., "12345")'
                },
                "groupId": {
                    "type": "string",
                    "description": 'Group ID as a numeric string (e.g., "67890")'
                },
                "requesterId": {
                    "type": "string",
                    "description": 'Requester user ID as a numeric string (e.g., "11111")'
                },
                "customFields": {
                    "type": "string",
                    "description": 'Custom fields as JSON object (e.g., {"field_id": "value"})'
                },
            },
            "required": ["email", "apiToken", "subdomain", "description"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("email") if context else None
        api_token = context.get("apiToken") if context else None
        subdomain = context.get("subdomain") if context else None
        if not all([email, api_token, subdomain]) or self._is_placeholder_token(email) or self._is_placeholder_token(api_token) or self._is_placeholder_token(subdomain):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }
        url = f"https://{subdomain}.zendesk.com/api/v2/tickets"

        ticket = {
            "comment": {"body": parameters.get("description", "")},
        }
        subject = parameters.get("subject")
        if subject:
            ticket["subject"] = subject
        if priority := parameters.get("priority"):
            ticket["priority"] = priority
        if status := parameters.get("status"):
            ticket["status"] = status
        if typ := parameters.get("type"):
            ticket["type"] = typ
        if assignee_id := parameters.get("assigneeId"):
            ticket["assignee_id"] = assignee_id
        if group_id := parameters.get("groupId"):
            ticket["group_id"] = group_id
        if requester_id := parameters.get("requesterId"):
            ticket["requester_id"] = requester_id
        if tags := parameters.get("tags"):
            ticket["tags"] = [t.strip() for t in tags.split(",")]
        if custom_fields_str := parameters.get("customFields"):
            try:
                custom_dict = json.loads(custom_fields_str)
                ticket["custom_fields"] = [{"id": str(k), "value": v} for k, v in custom_dict.items()]
            except json.JSONDecodeError:
                pass

        json_body = {"ticket": ticket}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
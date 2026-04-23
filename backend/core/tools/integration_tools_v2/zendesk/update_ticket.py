from typing import Any, Dict
import httpx
import base64
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskUpdateTicketTool(BaseTool):
    name = "zendesk_update_ticket"
    description = "Update an existing ticket in Zendesk with support for custom fields"
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
                "ticketId": {
                    "type": "string",
                    "description": "Ticket ID to update as a numeric string (e.g., \"12345\")",
                },
                "subject": {
                    "type": "string",
                    "description": "New ticket subject text",
                },
                "comment": {
                    "type": "string",
                    "description": "Comment text to add to the ticket",
                },
                "priority": {
                    "type": "string",
                    "description": 'Priority: "low", "normal", "high", or "urgent"',
                },
                "status": {
                    "type": "string",
                    "description": 'Status: "new", "open", "pending", "hold", "solved", or "closed"',
                },
                "type": {
                    "type": "string",
                    "description": 'Type: "problem", "incident", "question", or "task"',
                },
                "tags": {
                    "type": "string",
                    "description": 'Comma-separated tags (e.g., "billing, urgent")',
                },
                "assigneeId": {
                    "type": "string",
                    "description": 'Assignee user ID as a numeric string (e.g., "12345")',
                },
                "groupId": {
                    "type": "string",
                    "description": 'Group ID as a numeric string (e.g., "67890")',
                },
                "customFields": {
                    "type": "string",
                    "description": 'Custom fields as JSON object (e.g., {"field_id": "value"})',
                },
            },
            "required": ["ticketId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        email = context.get("zendesk_email") if context else None
        api_token = context.get("zendesk_api_token") if context else None
        subdomain = context.get("zendesk_subdomain") if context else None

        creds = [email, api_token, subdomain]
        if not all(creds) or any(self._is_placeholder_token(cred) for cred in creds if cred):
            return ToolResult(success=False, output="", error="Zendesk credentials not configured.")

        ticket_id = parameters["ticketId"]
        ticket: Dict[str, Any] = {}

        subject = parameters.get("subject")
        if subject:
            ticket["subject"] = subject

        priority = parameters.get("priority")
        if priority:
            ticket["priority"] = priority

        status = parameters.get("status")
        if status:
            ticket["status"] = status

        typ = parameters.get("type")
        if typ:
            ticket["type"] = typ

        assignee_id = parameters.get("assigneeId")
        if assignee_id:
            ticket["assignee_id"] = assignee_id

        group_id = parameters.get("groupId")
        if group_id:
            ticket["group_id"] = group_id

        tags = parameters.get("tags")
        if tags:
            ticket["tags"] = [t.strip() for t in tags.split(",")]

        comment = parameters.get("comment")
        if comment:
            ticket["comment"] = {"body": comment}

        custom_fields = parameters.get("customFields")
        if custom_fields:
            try:
                custom_fields_dict = json.loads(custom_fields)
                ticket["custom_fields"] = [{"id": k, "value": v} for k, v in custom_fields_dict.items()]
            except json.JSONDecodeError:
                pass

        body = {"ticket": ticket}

        credentials_str = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}.json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_content = response.text
                    try:
                        error_data = response.json()
                        error_content = str(error_data)
                    except:
                        pass
                    return ToolResult(
                        success=False, output="", error=f"API error {response.status_code}: {error_content}"
                    )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import base64
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZendeskGetTicketsTool(BaseTool):
    name = "zendesk_get_tickets"
    description = "Retrieve a list of tickets from Zendesk with optional filtering"
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
                key="api_token",
                description="Zendesk API token",
                env_var="ZENDESK_API_TOKEN",
                required=True,
                auth_type="api_key",
            ),
            CredentialRequirement(
                key="subdomain",
                description="Your Zendesk subdomain (e.g., \"mycompany\" for mycompany.zendesk.com)",
                env_var="ZENDESK_SUBDOMAIN",
                required=True,
                auth_type="api_key",
            ),
        ]

    def _resolve_zendesk_creds(self, context: dict | None) -> dict | None:
        if context is None:
            return None
        creds: dict[str, str] = {}
        required_keys = ["email", "api_token", "subdomain"]
        for key in required_keys:
            value = context.get(key)
            if value is None or self._is_placeholder_token(value):
                return None
            creds[key] = value
        return creds

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": 'Filter by status: "new", "open", "pending", "hold", "solved", or "closed"',
                },
                "priority": {
                    "type": "string",
                    "description": 'Filter by priority: "low", "normal", "high", or "urgent"',
                },
                "type": {
                    "type": "string",
                    "description": 'Filter by type: "problem", "incident", "question", or "task"',
                },
                "assigneeId": {
                    "type": "string",
                    "description": "Filter by assignee user ID as a numeric string (e.g., \"12345\")",
                },
                "organizationId": {
                    "type": "string",
                    "description": "Filter by organization ID as a numeric string (e.g., \"67890\")",
                },
                "sort": {
                    "type": "string",
                    "description": 'Sort field for ticket listing (only applies without filters): "updated_at", "id", or "status". Prefix with "-" for descending (e.g., "-updated_at")',
                },
                "perPage": {
                    "type": "string",
                    "description": "Results per page as a number string (default: \"100\", max: \"100\")",
                },
                "pageAfter": {
                    "type": "string",
                    "description": "Cursor from a previous response to fetch the next page of results",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        creds = self._resolve_zendesk_creds(context)
        if creds is None:
            return ToolResult(success=False, output="", error="Zendesk credentials (email, api_token, subdomain) not configured.")

        email: str = creds["email"]
        api_token: str = creds["api_token"]
        subdomain: str = creds["subdomain"]

        status = parameters.get("status")
        priority = parameters.get("priority")
        ticket_type = parameters.get("type")
        assignee_id = parameters.get("assigneeId")
        organization_id = parameters.get("organizationId")
        sort = parameters.get("sort")
        per_page = parameters.get("perPage", "100")
        page_after = parameters.get("pageAfter")

        has_filters = bool(status or priority or ticket_type or assignee_id or organization_id)

        base_url = f"https://{subdomain}.zendesk.com/api/v2"

        query_params: dict[str, str] = {}
        if has_filters:
            search_terms: list[str] = ["type:ticket"]
            if status:
                search_terms.append(f"status:{status}")
            if priority:
                search_terms.append(f"priority:{priority}")
            if ticket_type:
                search_terms.append(f"ticket_type:{ticket_type}")
            if assignee_id:
                search_terms.append(f"assignee_id:{assignee_id}")
            if organization_id:
                search_terms.append(f"organization_id:{organization_id}")
            query_params["query"] = " ".join(search_terms)
            query_params["filter[type]"] = "ticket"
        else:
            if sort:
                query_params["sort"] = sort

        if page_after:
            query_params["page[after]"] = page_after
        if per_page:
            query_params["per_page"] = per_page

        query_string = urlencode(query_params) if query_params else ""
        if has_filters:
            url = f"{base_url}/search/export"
        else:
            url = f"{base_url}/tickets"
        if query_string:
            url += f"?{query_string}"

        credentials = f"{email}/token:{api_token}"
        base64_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {
            "Authorization": f"Basic {base64_credentials}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    tickets = data.get("tickets", data.get("results", []))
                    next_page = data.get("next_page")
                    paging = {
                        "after_cursor": next_page,
                        "has_more": bool(next_page),
                    }
                    output_data = {
                        "tickets": tickets,
                        "paging": paging,
                        "metadata": {
                            "total_returned": len(tickets),
                            "has_more": paging["has_more"],
                        },
                        "success": True,
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
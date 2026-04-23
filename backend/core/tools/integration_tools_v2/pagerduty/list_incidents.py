from typing import Any, Dict, List
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PagerDutyListIncidentsTool(BaseTool):
    name = "pagerduty_list_incidents"
    description = "List incidents from PagerDuty with optional filters."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PAGERDUTY_API_KEY",
                description="PagerDuty REST API Key",
                env_var="PAGERDUTY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "statuses": {
                    "type": "string",
                    "description": "Comma-separated statuses to filter (triggered, acknowledged, resolved)",
                },
                "serviceIds": {
                    "type": "string",
                    "description": "Comma-separated service IDs to filter",
                },
                "since": {
                    "type": "string",
                    "description": "Start date filter (ISO 8601 format)",
                },
                "until": {
                    "type": "string",
                    "description": "End date filter (ISO 8601 format)",
                },
                "sortBy": {
                    "type": "string",
                    "description": "Sort field (e.g., created_at:desc)",
                },
                "limit": {
                    "type": "string",
                    "description": "Maximum number of results (max 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = context.get("PAGERDUTY_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="PagerDuty API key not configured.")

        statuses = parameters.get("statuses")
        service_ids = parameters.get("serviceIds")
        since = parameters.get("since")
        until = parameters.get("until")
        sort_by = parameters.get("sortBy")
        limit = parameters.get("limit")

        query_params: dict = {}
        if statuses:
            query_params["statuses[]"] = [s.strip() for s in statuses.split(",") if s.strip()]
        if service_ids:
            query_params["service_ids[]"] = [sid.strip() for sid in service_ids.split(",") if sid.strip()]
        if since:
            query_params["since"] = since
        if until:
            query_params["until"] = until
        if sort_by:
            query_params["sort_by"] = sort_by
        if limit:
            query_params["limit"] = limit
        query_params["include[]"] = ["services"]

        url = "https://api.pagerduty.com/incidents"
        headers = {
            "Authorization": f"Token token={api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                try:
                    data = response.json()
                except:
                    data = {}

                if response.status_code != 200:
                    error_msg = (
                        data.get("error", {}).get("message")
                        if isinstance(data, dict)
                        else response.text
                    )
                    return ToolResult(
                        success=False, output="", error=f"PagerDuty API error: {error_msg}"
                    )

                incidents = []
                for inc in data.get("incidents", []):
                    service = inc.get("service", {})
                    assignments = inc.get("assignments", [])
                    assignee_name = None
                    assignee_id = None
                    if assignments:
                        first_assignment = assignments[0]
                        assignee = first_assignment.get("assignee", {})
                        if assignee:
                            assignee_name = assignee.get("summary")
                            assignee_id = assignee.get("id")
                    escalation_policy = inc.get("escalation_policy", {})

                    incidents.append({
                        "id": inc.get("id"),
                        "incidentNumber": inc.get("incident_number"),
                        "title": inc.get("title"),
                        "status": inc.get("status"),
                        "urgency": inc.get("urgency"),
                        "createdAt": inc.get("created_at"),
                        "updatedAt": inc.get("updated_at"),
                        "serviceName": service.get("summary"),
                        "serviceId": service.get("id"),
                        "assigneeName": assignee_name,
                        "assigneeId": assignee_id,
                        "escalationPolicyName": escalation_policy.get("summary"),
                        "htmlUrl": inc.get("html_url"),
                    })

                result = {
                    "incidents": incidents,
                    "total": data.get("total", 0),
                    "more": data.get("more", False),
                }
                return ToolResult(success=True, output=json.dumps(result), data=result)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
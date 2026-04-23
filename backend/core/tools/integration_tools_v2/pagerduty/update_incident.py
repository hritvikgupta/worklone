from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PagerDutyUpdateIncidentTool(BaseTool):
    name = "pagerduty_update_incident"
    description = "Update an incident in PagerDuty (acknowledge, resolve, change urgency, etc.)."
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
            ),
            CredentialRequirement(
                key="PAGERDUTY_FROM_EMAIL",
                description="Email address of a valid PagerDuty user",
                env_var="PAGERDUTY_FROM_EMAIL",
                required=True,
                auth_type="api_key",
            ),
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pagerduty",
            context=context,
            context_token_keys=("PAGERDUTY_API_KEY",),
            env_token_keys=("PAGERDUTY_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    async def _resolve_from_email(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pagerduty",
            context=context,
            context_token_keys=("PAGERDUTY_FROM_EMAIL",),
            env_token_keys=("PAGERDUTY_FROM_EMAIL",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "incidentId": {
                    "type": "string",
                    "description": "ID of the incident to update",
                },
                "status": {
                    "type": "string",
                    "description": "New status (acknowledged or resolved)",
                },
                "title": {
                    "type": "string",
                    "description": "New incident title",
                },
                "urgency": {
                    "type": "string",
                    "description": "New urgency (high or low)",
                },
                "escalationLevel": {
                    "type": "string",
                    "description": "Escalation level to escalate to",
                },
            },
            "required": ["incidentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        from_email = await self._resolve_from_email(context)

        if self._is_placeholder_token(api_key) or self._is_placeholder_token(from_email):
            return ToolResult(success=False, output="", error="Credentials not configured.")

        headers = {
            "Authorization": f"Token token={api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
            "From": from_email,
        }

        incident_id = parameters["incidentId"].strip()
        url = f"https://api.pagerduty.com/incidents/{incident_id}"

        incident = {
            "id": parameters["incidentId"],
            "type": "incident",
        }
        status = parameters.get("status")
        if status:
            incident["status"] = status
        title = parameters.get("title")
        if title:
            incident["title"] = title
        urgency = parameters.get("urgency")
        if urgency:
            incident["urgency"] = urgency
        escalation_level = parameters.get("escalationLevel")
        if escalation_level:
            incident["escalation_level"] = int(escalation_level)
        body = {"incident": incident}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PagerDutyCreateIncidentTool(BaseTool):
    name = "pagerduty_create_incident"
    description = "Create a new incident in PagerDuty."
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
                "fromEmail": {
                    "type": "string",
                    "description": "Email address of a valid PagerDuty user"
                },
                "title": {
                    "type": "string",
                    "description": "Incident title/summary"
                },
                "serviceId": {
                    "type": "string",
                    "description": "ID of the PagerDuty service"
                },
                "urgency": {
                    "type": "string",
                    "description": "Urgency level (high or low)"
                },
                "body": {
                    "type": "string",
                    "description": "Detailed description of the incident"
                },
                "escalationPolicyId": {
                    "type": "string",
                    "description": "Escalation policy ID to assign"
                },
                "assigneeId": {
                    "type": "string",
                    "description": "User ID to assign the incident to"
                }
            },
            "required": ["fromEmail", "title", "serviceId"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("PAGERDUTY_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="PagerDuty API key not configured.")
        
        headers = {
            "Authorization": f"Token token={api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
            "From": parameters["fromEmail"],
        }
        
        incident: Dict[str, Any] = {
            "type": "incident",
            "title": parameters["title"],
            "service": {
                "id": parameters["serviceId"],
                "type": "service_reference",
            },
        }
        
        if parameters.get("urgency"):
            incident["urgency"] = parameters["urgency"]
        if parameters.get("body"):
            incident["body"] = {
                "type": "incident_body",
                "details": parameters["body"],
            }
        if parameters.get("escalationPolicyId"):
            incident["escalation_policy"] = {
                "id": parameters["escalationPolicyId"],
                "type": "escalation_policy_reference",
            }
        if parameters.get("assigneeId"):
            incident["assignments"] = [
                {
                    "assignee": {
                        "id": parameters["assigneeId"],
                        "type": "user_reference",
                    },
                }
            ]
        
        json_body = {"incident": incident}
        url = "https://api.pagerduty.com/incidents"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
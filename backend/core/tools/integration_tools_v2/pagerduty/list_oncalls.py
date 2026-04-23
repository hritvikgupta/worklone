from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PagerDutyListOncallsTool(BaseTool):
    name = "pagerduty_list_oncalls"
    description = "List current on-call entries from PagerDuty."
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
                "escalationPolicyIds": {
                    "type": "string",
                    "description": "Comma-separated escalation policy IDs to filter",
                },
                "scheduleIds": {
                    "type": "string",
                    "description": "Comma-separated schedule IDs to filter",
                },
                "since": {
                    "type": "string",
                    "description": "Start time filter (ISO 8601 format)",
                },
                "until": {
                    "type": "string",
                    "description": "End time filter (ISO 8601 format)",
                },
                "limit": {
                    "type": "string",
                    "description": "Maximum number of results (max 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("PAGERDUTY_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="PagerDuty API key not configured.")
        
        headers = {
            "Authorization": f"Token token={api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
        }
        
        query_params: Dict[str, Any] = {}
        escalation_policy_ids = parameters.get("escalationPolicyIds")
        if escalation_policy_ids:
            query_params["escalation_policy_ids[]"] = [id_str.strip() for id_str in escalation_policy_ids.split(",")]
        schedule_ids = parameters.get("scheduleIds")
        if schedule_ids:
            query_params["schedule_ids[]"] = [id_str.strip() for id_str in schedule_ids.split(",")]
        since = parameters.get("since")
        if since:
            query_params["since"] = since
        until = parameters.get("until")
        if until:
            query_params["until"] = until
        limit = parameters.get("limit")
        if limit:
            query_params["limit"] = limit
        
        url = "https://api.pagerduty.com/oncalls"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict, List
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class PagerDutyListServicesTool(BaseTool):
    name = "pagerduty_list_services"
    description = "List services from PagerDuty with optional name filter."
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
                "query": {
                    "type": "string",
                    "description": "Filter services by name",
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
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="PagerDuty API key not configured.")
        
        headers = {
            "Authorization": f"Token token={api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
        }
        
        url = "https://api.pagerduty.com/services"
        params: Dict[str, str] = {}
        if query := parameters.get("query"):
            params["query"] = str(query)
        if limit := parameters.get("limit"):
            params["limit"] = str(limit)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    services: List[Dict[str, Any]] = []
                    for svc in data.get("services", []):
                        esc = svc.get("escalation_policy", {})
                        services.append({
                            "id": svc.get("id"),
                            "name": svc.get("name"),
                            "description": svc.get("description"),
                            "status": svc.get("status"),
                            "escalationPolicyName": esc.get("summary"),
                            "escalationPolicyId": esc.get("id"),
                            "createdAt": svc.get("created_at"),
                            "htmlUrl": svc.get("html_url"),
                        })
                    output_data = {
                        "services": services,
                        "total": data.get("total", 0),
                        "more": data.get("more", False),
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=f"PagerDuty API error: {error_msg}")
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
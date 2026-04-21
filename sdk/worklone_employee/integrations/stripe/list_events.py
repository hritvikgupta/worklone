from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeListEventsTool(BaseTool):
    name = "stripe_list_events"
    description = "List all Events"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="STRIPE_API_KEY",
                description="Stripe API key (secret key)",
                env_var="STRIPE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Number of results to return (default 10, max 100)",
                },
                "type": {
                    "type": "string",
                    "description": "Filter by event type (e.g., payment_intent.created)",
                },
                "created": {
                    "type": "object",
                    "description": "Filter by creation date (e.g., {\"gt\": 1633024800})",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("STRIPE_API_KEY") if context else None
        
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        url = "https://api.stripe.com/v1/events"
        params: Dict[str, Any] = {}
        
        limit = parameters.get("limit")
        if limit is not None:
            params["limit"] = limit
        
        event_type = parameters.get("type")
        if event_type is not None:
            params["type"] = event_type
        
        created = parameters.get("created")
        if isinstance(created, dict):
            for key, value in created.items():
                params[f"created[{key}]"] = str(value)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
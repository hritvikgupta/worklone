import httpx
import os
from typing import Dict
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeSearchSubscriptionsTool(BaseTool):
    name = "stripe_search_subscriptions"
    description = "Search for subscriptions using query syntax"
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

    def _get_api_key(self, context: dict | None) -> str | None:
        api_key = context.get("STRIPE_API_KEY") if context else None
        if api_key is None:
            api_key = os.getenv("STRIPE_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return None
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., \"status:'active' AND customer:'cus_xxx'\")",
                },
                "limit": {
                    "type": "number",
                    "description": "Number of results to return (default 10, max 100)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)
        if api_key is None:
            return ToolResult(success=False, output="", error="Stripe API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = "https://api.stripe.com/v1/subscriptions/search"
        params_dict = {
            "query": parameters["query"],
        }
        limit = parameters.get("limit")
        if limit is not None:
            params_dict["limit"] = limit

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
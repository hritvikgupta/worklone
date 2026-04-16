from typing import Any, Dict
import httpx
import json
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeListPaymentIntentsTool(BaseTool):
    name = "stripe_list_payment_intents"
    description = "List all Payment Intents"
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("STRIPE_API_KEY") if context else None
        if not api_key:
            api_key = os.environ.get("STRIPE_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Number of results to return (default 10, max 100)",
                },
                "customer": {
                    "type": "string",
                    "description": "Filter by customer ID",
                },
                "created": {
                    "type": "object",
                    "description": "Filter by creation date (e.g., {\"gt\": 1633024800})",
                },
            },
            "required": [],
        }

    def _build_params(self, parameters: dict) -> dict[str, Any]:
        params: dict[str, Any] = {}
        limit = parameters.get("limit")
        if limit is not None:
            params["limit"] = limit
        customer = parameters.get("customer")
        if customer is not None:
            params["customer"] = customer
        created = parameters.get("created")
        if isinstance(created, dict):
            for key, value in created.items():
                params[f"created[{key}]"] = str(value)
        return params

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = "https://api.stripe.com/v1/payment_intents"
        query_params = self._build_params(parameters)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code == 200:
                    data = response.json()
                    transformed = {
                        "payment_intents": data.get("data", []),
                        "metadata": {
                            "count": len(data.get("data", [])),
                            "has_more": data.get("has_more", False),
                        },
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(transformed, indent=2),
                        data=transformed,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
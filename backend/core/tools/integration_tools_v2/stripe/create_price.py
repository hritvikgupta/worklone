from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class StripeCreatePriceTool(BaseTool):
    name = "stripe_create_price"
    description = "Create a new price for a product"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "stripe",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("STRIPE_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "product": {
                    "type": "string",
                    "description": "Product ID (e.g., prod_1234567890)",
                },
                "currency": {
                    "type": "string",
                    "description": "Three-letter ISO currency code (e.g., usd, eur)",
                },
                "unit_amount": {
                    "type": "number",
                    "description": "Amount in cents (e.g., 1000 for $10.00)",
                },
                "recurring": {
                    "type": "object",
                    "description": "Recurring billing configuration (interval: day/week/month/year)",
                },
                "metadata": {
                    "type": "object",
                    "description": "Set of key-value pairs",
                },
                "billing_scheme": {
                    "type": "string",
                    "description": "Billing scheme (per_unit or tiered)",
                },
            },
            "required": ["product", "currency"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = "https://api.stripe.com/v1/prices"
        
        data: Dict[str, str] = {
            "product": parameters["product"],
            "currency": parameters["currency"],
        }
        
        unit_amount = parameters.get("unit_amount")
        if unit_amount is not None:
            data["unit_amount"] = str(unit_amount)
        
        billing_scheme = parameters.get("billing_scheme")
        if billing_scheme:
            data["billing_scheme"] = billing_scheme
        
        recurring = parameters.get("recurring", {})
        for key, value in recurring.items():
            if value:
                data[f"recurring[{key}]"] = str(value)
        
        metadata = parameters.get("metadata", {})
        for key, value in metadata.items():
            data[f"metadata[{key}]"] = str(value)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)
                
                if response.status_code in [200, 201, 204]:
                    response_data = response.json()
                    metadata = {
                        "id": response_data.get("id"),
                        "product": response_data.get("product"),
                        "unit_amount": response_data.get("unit_amount"),
                        "currency": response_data.get("currency"),
                    }
                    output_data = {
                        "price": response_data,
                        "metadata": metadata,
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
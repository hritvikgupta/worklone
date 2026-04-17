from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class StripeCreatePaymentIntentTool(BaseTool):
    name = "stripe_create_payment_intent"
    description = "Create a new Payment Intent to process a payment"
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
            context_token_keys=("api_key",),
            env_token_keys=("STRIPE_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Amount in cents (e.g., 2000 for $20.00)",
                },
                "currency": {
                    "type": "string",
                    "description": "Three-letter ISO currency code (e.g., usd, eur)",
                },
                "customer": {
                    "type": "string",
                    "description": "Customer ID to associate with this payment",
                },
                "payment_method": {
                    "type": "string",
                    "description": "Payment method ID",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the payment",
                },
                "receipt_email": {
                    "type": "string",
                    "description": "Email address to send receipt to",
                },
                "metadata": {
                    "type": "object",
                    "description": "Set of key-value pairs for storing additional information",
                },
                "automatic_payment_methods": {
                    "type": "object",
                    "description": "Enable automatic payment methods (e.g., {\"enabled\": true})",
                },
            },
            "required": ["amount", "currency"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = "https://api.stripe.com/v1/payment_intents"
        
        body_data: Dict[str, str] = {}
        amount = parameters["amount"]
        body_data["amount"] = str(int(amount))
        body_data["currency"] = parameters["currency"]
        
        customer = parameters.get("customer")
        if customer:
            body_data["customer"] = customer
        
        payment_method = parameters.get("payment_method")
        if payment_method:
            body_data["payment_method"] = payment_method
        
        description = parameters.get("description")
        if description:
            body_data["description"] = description
        
        receipt_email = parameters.get("receipt_email")
        if receipt_email:
            body_data["receipt_email"] = receipt_email
        
        metadata = parameters.get("metadata", {})
        for key, value in metadata.items():
            body_data[f"metadata[{key}]"] = str(value)
        
        automatic_payment_methods = parameters.get("automatic_payment_methods", {})
        if automatic_payment_methods.get("enabled"):
            body_data["automatic_payment_methods[enabled]"] = "true"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=body_data)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
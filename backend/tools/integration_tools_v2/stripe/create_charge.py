from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class StripeCreateChargeTool(BaseTool):
    name = "stripe_create_charge"
    description = "Create a new charge to process a payment"
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
            context_token_keys=("STRIPE_API_KEY",),
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
                    "description": "Customer ID to associate with this charge",
                },
                "source": {
                    "type": "string",
                    "description": "Payment source ID (e.g., card token or saved card ID)",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the charge",
                },
                "metadata": {
                    "type": "object",
                    "description": "Set of key-value pairs for storing additional information",
                },
                "capture": {
                    "type": "boolean",
                    "description": "Whether to immediately capture the charge (defaults to true)",
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
        
        url = "https://api.stripe.com/v1/charges"
        
        form_data = {
            "amount": str(int(parameters["amount"])),
            "currency": parameters["currency"],
        }
        if "customer" in parameters:
            form_data["customer"] = parameters["customer"]
        if "source" in parameters:
            form_data["source"] = parameters["source"]
        if "description" in parameters:
            form_data["description"] = parameters["description"]
        if "capture" in parameters:
            form_data["capture"] = str(parameters["capture"]).lower()
        if "metadata" in parameters and parameters["metadata"]:
            for key, value in parameters["metadata"].items():
                form_data[f"metadata[{key}]"] = str(value)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=form_data)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
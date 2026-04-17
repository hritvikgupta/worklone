from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeUpdatePaymentIntentTool(BaseTool):
    name = "stripe_update_payment_intent"
    description = "Update an existing Payment Intent"
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

    def _resolve_api_key(self, context: dict | None) -> str | None:
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
                "id": {
                    "type": "string",
                    "description": "Payment Intent ID (e.g., pi_1234567890)",
                },
                "amount": {
                    "type": "number",
                    "description": "Updated amount in cents",
                },
                "currency": {
                    "type": "string",
                    "description": "Three-letter ISO currency code",
                },
                "customer": {
                    "type": "string",
                    "description": "Customer ID",
                },
                "description": {
                    "type": "string",
                    "description": "Updated description",
                },
                "metadata": {
                    "type": "object",
                    "description": "Updated metadata",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        if api_key is None:
            return ToolResult(success=False, output="", error="Stripe API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        id_ = parameters["id"]
        url = f"https://api.stripe.com/v1/payment_intents/{id_}"

        form_data: Dict[str, str] = {}
        if "amount" in parameters:
            form_data["amount"] = str(int(parameters["amount"]))
        if "currency" in parameters:
            form_data["currency"] = parameters["currency"]
        if "customer" in parameters:
            form_data["customer"] = parameters["customer"]
        if "description" in parameters:
            form_data["description"] = parameters["description"]
        if "metadata" in parameters and isinstance(parameters["metadata"], dict):
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
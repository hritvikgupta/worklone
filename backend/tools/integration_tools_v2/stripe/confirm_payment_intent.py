from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeConfirmPaymentIntentTool(BaseTool):
    name = "stripe_confirm_payment_intent"
    description = "Confirm a Payment Intent to complete the payment"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="stripe_api_key",
                description="Stripe API key (secret key)",
                env_var="STRIPE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        access_token = None
        if context is not None:
            access_token = context.get("stripe_api_key")
        if access_token is None:
            access_token = os.getenv("STRIPE_API_KEY")
        return access_token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Payment Intent ID (e.g., pi_1234567890)",
                },
                "payment_method": {
                    "type": "string",
                    "description": "Payment method ID to confirm with",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = f"https://api.stripe.com/v1/payment_intents/{parameters['id']}/confirm"

        data: Dict[str, str] = {}
        payment_method = parameters.get("payment_method")
        if payment_method:
            data["payment_method"] = payment_method

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
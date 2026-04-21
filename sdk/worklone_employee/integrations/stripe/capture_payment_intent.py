from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeCapturePaymentIntentTool(BaseTool):
    name = "stripe_capture_payment_intent"
    description = "Capture an authorized Payment Intent"
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
                "id": {
                    "type": "string",
                    "description": "Payment Intent ID (e.g., pi_1234567890)",
                },
                "amount_to_capture": {
                    "type": "number",
                    "description": "Amount to capture in cents (defaults to full amount)",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("STRIPE_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        url = f"https://api.stripe.com/v1/payment_intents/{parameters['id']}/capture"

        data: Dict[str, str] = {}
        if "amount_to_capture" in parameters:
            data["amount_to_capture"] = str(int(parameters["amount_to_capture"]))

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
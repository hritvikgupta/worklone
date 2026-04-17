from typing import Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeCancelPaymentIntentTool(BaseTool):
    name = "stripe_cancel_payment_intent"
    description = "Cancel a Payment Intent"
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
                "cancellation_reason": {
                    "type": "string",
                    "description": "Reason for cancellation (duplicate, fraudulent, requested_by_customer, abandoned)",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("STRIPE_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")
        
        id_ = parameters.get("id")
        if not id_:
            return ToolResult(success=False, output="", error="Payment Intent ID is required.")
        
        url = f"https://api.stripe.com/v1/payment_intents/{id_}/cancel"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        data: Dict[str, str] = {}
        cancellation_reason = parameters.get("cancellation_reason")
        if cancellation_reason:
            data["cancellation_reason"] = cancellation_reason
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
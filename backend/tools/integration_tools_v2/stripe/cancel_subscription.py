from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeCancelSubscriptionTool(BaseTool):
    name = "stripe_cancel_subscription"
    description = "Cancel a subscription"
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
        token = context.get("stripe_api_key") if context else None
        if token is None:
            token = os.getenv("STRIPE_API_KEY")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Subscription ID (e.g., sub_1234567890)",
                },
                "prorate": {
                    "type": "boolean",
                    "description": "Whether to prorate the cancellation",
                },
                "invoice_now": {
                    "type": "boolean",
                    "description": "Whether to invoice immediately",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = f"https://api.stripe.com/v1/subscriptions/{parameters['id']}"
        
        data = {}
        prorate = parameters.get("prorate")
        if prorate is not None:
            data["prorate"] = str(prorate).lower()
        invoice_now = parameters.get("invoice_now")
        if invoice_now is not None:
            data["invoice_now"] = str(invoice_now).lower()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers, data=data)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
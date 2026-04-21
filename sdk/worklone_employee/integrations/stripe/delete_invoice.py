import os
from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeDeleteInvoiceTool(BaseTool):
    name = "stripe_delete_invoice"
    description = "Permanently delete a draft invoice"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="STRIPE_SECRET_KEY",
                description="Stripe API key (secret key)",
                env_var="STRIPE_SECRET_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_access_token(self, context: dict | None) -> str:
        api_key = context.get("STRIPE_SECRET_KEY") if context else None
        if api_key is None:
            api_key = os.getenv("STRIPE_SECRET_KEY")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Invoice ID (e.g., in_1234567890)",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = f"https://api.stripe.com/v1/invoices/{parameters['id']}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeCreateSubscriptionTool(BaseTool):
    name = "Stripe Create Subscription"
    description = "Create a new subscription for a customer"
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
        api_key = context.get("STRIPE_API_KEY") if context else None
        if self._is_placeholder_token(api_key or ""):
            return ""
        return api_key

    def _build_form_data(self, params: dict) -> Dict[str, str]:
        form_data: Dict[str, str] = {}
        form_data["customer"] = params["customer"]
        items = params["items"]
        for index, item in enumerate(items):
            form_data[f"items[{index}][price]"] = item["price"]
            quantity = item.get("quantity")
            if quantity is not None:
                form_data[f"items[{index}][quantity]"] = str(int(quantity))
        trial_period_days = params.get("trial_period_days")
        if trial_period_days is not None:
            form_data["trial_period_days"] = str(int(trial_period_days))
        dpm = params.get("default_payment_method")
        if dpm:
            form_data["default_payment_method"] = dpm
        cae = params.get("cancel_at_period_end")
        if cae is not None:
            form_data["cancel_at_period_end"] = "true" if cae else "false"
        metadata = params.get("metadata")
        if isinstance(metadata, dict):
            for key, value in metadata.items():
                form_data[f"metadata[{key}]"] = str(value)
        return form_data

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer ID to subscribe"
                },
                "items": {
                    "type": "array",
                    "description": 'Array of items with price IDs (e.g., [{"price": "price_xxx", "quantity": 1}])',
                    "items": {
                        "type": "object",
                        "properties": {
                            "price": {
                                "type": "string"
                            },
                            "quantity": {
                                "type": "integer"
                            }
                        },
                        "required": ["price"]
                    }
                },
                "trial_period_days": {
                    "type": "number",
                    "description": "Number of trial days"
                },
                "default_payment_method": {
                    "type": "string",
                    "description": "Payment method ID"
                },
                "cancel_at_period_end": {
                    "type": "boolean",
                    "description": "Cancel subscription at period end"
                },
                "metadata": {
                    "type": "object",
                    "description": "Set of key-value pairs for storing additional information"
                }
            },
            "required": ["customer", "items"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = "https://api.stripe.com/v1/subscriptions"
        form_data = self._build_form_data(parameters)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=form_data)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeRetrieveProductTool(BaseTool):
    name = "stripe_retrieve_product"
    description = "Retrieve an existing product by ID"
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
                    "description": "Product ID (e.g., prod_1234567890)",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("STRIPE_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")
        
        product_id = parameters["id"]
        url = f"https://api.stripe.com/v1/products/{product_id}"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
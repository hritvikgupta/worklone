from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeUpdateInvoiceTool(BaseTool):
    name = "stripe_update_invoice"
    description = "Update an existing invoice"
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("STRIPE_API_KEY") if context else None
        if api_key is None:
            api_key = os.getenv("STRIPE_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Invoice ID (e.g., in_1234567890)",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the invoice",
                },
                "metadata": {
                    "type": "object",
                    "description": "Set of key-value pairs",
                },
                "auto_advance": {
                    "type": "boolean",
                    "description": "Auto-finalize the invoice",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        params = parameters
        url = f"https://api.stripe.com/v1/invoices/{params['id']}"
        
        form_data: Dict[str, str] = {}
        if params.get("description"):
            form_data["description"] = params["description"]
        if "auto_advance" in params:
            form_data["auto_advance"] = str(params["auto_advance"]).lower()
        metadata = params.get("metadata")
        if metadata:
            for key, value in metadata.items():
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
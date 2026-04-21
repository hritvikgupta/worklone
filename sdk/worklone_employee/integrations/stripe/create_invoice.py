from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeCreateInvoiceTool(BaseTool):
    name = "stripe_create_invoice"
    description = "Create a new invoice"
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

    def _build_form_data(self, parameters: dict) -> dict[str, str]:
        form_data: dict[str, str] = {
            "customer": parameters["customer"],
        }
        description = parameters.get("description")
        if description:
            form_data["description"] = description
        collection_method = parameters.get("collection_method")
        if collection_method:
            form_data["collection_method"] = collection_method
        auto_advance = parameters.get("auto_advance")
        if auto_advance is not None:
            form_data["auto_advance"] = str(auto_advance).lower()
        metadata = parameters.get("metadata", {})
        for key, value in metadata.items():
            form_data[f"metadata[{key}]"] = str(value)
        return form_data

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer ID (e.g., cus_1234567890)",
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
                "collection_method": {
                    "type": "string",
                    "description": "Collection method: charge_automatically or send_invoice",
                },
            },
            "required": ["customer"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        stripe_api_key = context.get("STRIPE_API_KEY") if context else None
        
        if self._is_placeholder_token(stripe_api_key or ""):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {stripe_api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = "https://api.stripe.com/v1/invoices"
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
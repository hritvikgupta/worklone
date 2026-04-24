import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeFinalizeInvoiceTool(BaseTool):
    name = "stripe_finalize_invoice"
    description = "Finalize a draft invoice"
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
                    "description": "Invoice ID (e.g., in_1234567890)"
                },
                "auto_advance": {
                    "type": "boolean",
                    "description": "Auto-advance the invoice"
                }
            },
            "required": ["id"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("STRIPE_API_KEY") if context else None
        
        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        url = f"https://api.stripe.com/v1/invoices/{parameters['id']}/finalize"
        
        body_data = {}
        if parameters.get("auto_advance") is not None:
            body_data["auto_advance"] = str(parameters["auto_advance"]).lower()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=body_data)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
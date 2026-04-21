from typing import Any, Dict
import httpx
import os
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement

class StripeUpdateCustomerTool(BaseTool):
    name = "Stripe Update Customer"
    description = "Update an existing customer"
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
        candidate_tokens = []
        if context is not None:
            candidate_tokens.append(context.get("STRIPE_API_KEY"))
        candidate_tokens.append(os.environ.get("STRIPE_API_KEY"))
        for token in candidate_tokens:
            if token and not self._is_placeholder_token(token):
                return token
        return ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Customer ID (e.g., cus_1234567890)",
                },
                "email": {
                    "type": "string",
                    "description": "Updated email address",
                },
                "name": {
                    "type": "string",
                    "description": "Updated name",
                },
                "phone": {
                    "type": "string",
                    "description": "Updated phone number",
                },
                "description": {
                    "type": "string",
                    "description": "Updated description",
                },
                "address": {
                    "type": "object",
                    "description": "Updated address object",
                },
                "metadata": {
                    "type": "object",
                    "description": "Updated metadata",
                },
            },
            "required": ["id"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Stripe API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        customer_id = parameters["id"]
        url = f"https://api.stripe.com/v1/customers/{customer_id}"
        
        body_dict: Dict[str, str] = {}
        for field in ("email", "name", "phone", "description"):
            value = parameters.get(field)
            if value:
                body_dict[field] = str(value)
        
        address = parameters.get("address")
        if address:
            for key, value in address.items():
                if value:
                    body_dict[f"address[{key}]"] = str(value)
        
        metadata = parameters.get("metadata")
        if metadata:
            for key, value in metadata.items():
                if value:
                    body_dict[f"metadata[{key}]"] = str(value)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=body_dict)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
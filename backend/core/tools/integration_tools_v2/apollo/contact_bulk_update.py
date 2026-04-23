import httpx
import os
from typing import Any
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloContactBulkUpdateTool(BaseTool):
    name = "apollo_contact_bulk_update"
    description = "Update up to 100 existing contacts at once in your Apollo database. Each contact must include an id field. Master key required."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="APOLLO_API_KEY",
                description="Apollo API key (master key required)",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("APOLLO_API_KEY") if context else None
        if api_key is None:
            api_key = os.getenv("APOLLO_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "contacts": {
                    "type": "array",
                    "description": "Array of contacts to update (max 100). Each contact must include id field, and optionally first_name, last_name, email, title, account_id, owner_id",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Contact ID (required)"
                            },
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "email": {"type": "string"},
                            "title": {"type": "string"},
                            "account_id": {"type": "string"},
                            "owner_id": {"type": "string"}
                        },
                        "required": ["id"]
                    },
                    "maxItems": 100
                }
            },
            "required": ["contacts"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Apollo API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }
        
        url = "https://api.apollo.io/api/v1/contacts/bulk_update"
        body = {
            "contacts": parameters.get("contacts", [])[:100]
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class ApolloAccountBulkCreateTool(BaseTool):
    name = "apollo_account_bulk_create"
    description = "Create up to 100 accounts at once in your Apollo database. Note: Apollo does not apply deduplication - duplicate accounts may be created if entries share similar names or domains. Master key required."
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "apollo",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("APOLLO_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "accounts": {
                    "type": "array",
                    "description": "Array of accounts to create (max 100). Each account should include name (required), and optionally website_url, phone, owner_id",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Account name (required)"
                            },
                            "website_url": {
                                "type": "string",
                                "description": "Website URL (optional)"
                            },
                            "phone": {
                                "type": "string",
                                "description": "Phone number (optional)"
                            },
                            "owner_id": {
                                "type": "string",
                                "description": "Owner ID (optional)"
                            }
                        },
                        "required": ["name"]
                    }
                }
            },
            "required": ["accounts"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": access_token,
        }
        
        url = "https://api.apollo.io/api/v1/accounts/bulk_create"
        body = {
            "accounts": parameters["accounts"][:100]
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
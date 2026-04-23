from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ApolloContactUpdateTool(BaseTool):
    name = "apollo_contact_update"
    description = "Update an existing contact in your Apollo database"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="APOLLO_API_KEY",
                description="Apollo API key",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "apollo",
            context=context,
            context_token_keys=("APOLLO_API_KEY",),
            env_token_keys=("APOLLO_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "ID of the contact to update (e.g., \"con_abc123\")",
                },
                "first_name": {
                    "type": "string",
                    "description": "First name of the contact",
                },
                "last_name": {
                    "type": "string",
                    "description": "Last name of the contact",
                },
                "email": {
                    "type": "string",
                    "description": "Email address",
                },
                "title": {
                    "type": "string",
                    "description": "Job title (e.g., \"VP of Sales\", \"Software Engineer\")",
                },
                "account_id": {
                    "type": "string",
                    "description": "Apollo account ID (e.g., \"acc_abc123\")",
                },
                "owner_id": {
                    "type": "string",
                    "description": "User ID of the contact owner",
                },
            },
            "required": ["contact_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": access_token,
        }
        
        url = f"https://api.apollo.io/api/v1/contacts/{parameters['contact_id']}"
        
        fields = ["first_name", "last_name", "email", "title", "account_id", "owner_id"]
        body = {k: parameters[k] for k in fields if parameters.get(k)}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
import os
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloAccountUpdateTool(BaseTool):
    name = "apollo_account_update"
    description = "Update an existing account in your Apollo database"
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("APOLLO_API_KEY") if context else None
        api_key = api_key or os.environ.get("APOLLO_API_KEY")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "ID of the account to update (e.g., \"acc_abc123\")",
                },
                "name": {
                    "type": "string",
                    "description": "Company name (e.g., \"Acme Corporation\")",
                },
                "website_url": {
                    "type": "string",
                    "description": "Company website URL",
                },
                "phone": {
                    "type": "string",
                    "description": "Company phone number",
                },
                "owner_id": {
                    "type": "string",
                    "description": "User ID of the account owner",
                },
            },
            "required": ["account_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }

        account_id = parameters["account_id"]
        url = f"https://api.apollo.io/api/v1/accounts/{account_id}"

        body: Dict[str, Any] = {}
        if "name" in parameters and parameters["name"] is not None:
            body["name"] = parameters["name"]
        if "website_url" in parameters and parameters["website_url"] is not None:
            body["website_url"] = parameters["website_url"]
        if "phone" in parameters and parameters["phone"] is not None:
            body["phone"] = parameters["phone"]
        if "owner_id" in parameters and parameters["owner_id"] is not None:
            body["owner_id"] = parameters["owner_id"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
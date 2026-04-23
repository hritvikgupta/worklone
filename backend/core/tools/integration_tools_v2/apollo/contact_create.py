from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloContactCreateTool(BaseTool):
    name = "apollo_contact_create"
    description = "Create a new contact in your Apollo database"
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
        if api_key is None:
            api_key = os.getenv("APOLLO_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
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
                    "description": "Email address of the contact",
                },
                "title": {
                    "type": "string",
                    "description": 'Job title (e.g., "VP of Sales", "Software Engineer")',
                },
                "account_id": {
                    "type": "string",
                    "description": 'Apollo account ID to associate with (e.g., "acc_abc123")',
                },
                "owner_id": {
                    "type": "string",
                    "description": "User ID of the contact owner",
                },
            },
            "required": ["first_name", "last_name"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Apollo API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }

        body = {
            "first_name": parameters["first_name"],
            "last_name": parameters["last_name"],
        }
        for field in ["email", "title", "account_id", "owner_id"]:
            if parameters.get(field):
                body[field] = parameters[field]

        url = "https://api.apollo.io/api/v1/contacts"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
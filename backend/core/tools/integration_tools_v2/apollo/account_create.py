from typing import Any, Dict
import httpx
import os
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloAccountCreateTool(BaseTool):
    name = "apollo_account_create"
    description = "Create a new account (company) in your Apollo database"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Apollo API key",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = context.get("apiKey") if context else None
        if api_key is None:
            api_key = os.getenv("APOLLO_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            raise ValueError("API key not configured.")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Company name (e.g., \"Acme Corporation\")"
                },
                "website_url": {
                    "type": "string",
                    "description": "Company website URL"
                },
                "phone": {
                    "type": "string",
                    "description": "Company phone number"
                },
                "owner_id": {
                    "type": "string",
                    "description": "User ID of the account owner"
                }
            },
            "required": ["name"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            api_key = await self._resolve_api_key(context)
        except ValueError as e:
            return ToolResult(success=False, output="", error=str(e))

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }

        body: Dict[str, Any] = {"name": parameters["name"]}
        for field in ["website_url", "phone", "owner_id"]:
            if field in parameters and parameters[field]:
                body[field] = parameters[field]

        url = "https://api.apollo.io/api/v1/accounts"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if 200 <= response.status_code < 300:
                    data = response.json()
                    output_data = {
                        "account": data.get("account"),
                        "created": bool(data.get("account"))
                    }
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data
                    )
                else:
                    error_text = response.text
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Apollo API error: {response.status_code} - {error_text}"
                    )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
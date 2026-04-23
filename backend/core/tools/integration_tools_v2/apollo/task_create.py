from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloTaskCreateTool(BaseTool):
    name = "Apollo Create Task"
    description = "Create a new task in Apollo"
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

    def _resolve_api_key(self, context: dict | None) -> str | None:
        api_key = context.get("APOLLO_API_KEY") if context else None
        if api_key is None:
            api_key = os.getenv("APOLLO_API_KEY")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "Task note/description",
                },
                "contact_id": {
                    "type": "string",
                    "description": "Contact ID to associate with (e.g., \"con_abc123\")",
                },
                "account_id": {
                    "type": "string",
                    "description": "Account ID to associate with (e.g., \"acc_abc123\")",
                },
                "due_at": {
                    "type": "string",
                    "description": "Due date in ISO format",
                },
                "priority": {
                    "type": "string",
                    "description": "Task priority",
                },
                "type": {
                    "type": "string",
                    "description": "Task type",
                },
            },
            "required": ["note"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)

        if not api_key or self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }

        url = "https://api.apollo.io/api/v1/tasks/bulk_create"

        body = {"note": parameters["note"]}
        for key in ("contact_id", "account_id", "due_at", "priority", "type"):
            value = parameters.get(key)
            if value:
                body[key] = value

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
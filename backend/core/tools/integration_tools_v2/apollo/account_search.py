from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloAccountSearchTool(BaseTool):
    name = "apollo_account_search"
    description = "Search your team's accounts in Apollo. Display limit: 50,000 records (100 records per page, 500 pages max). Use filters to narrow results. Master key required."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Apollo API key (master key required)",
                env_var="APOLLO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> str | None:
        if context is None:
            return None
        value = context.get("apiKey")
        if value is None or self._is_placeholder_token(value):
            return None
        return value

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "q_keywords": {
                    "type": "string",
                    "description": "Keywords to search for in account data",
                },
                "owner_id": {
                    "type": "string",
                    "description": "Filter by account owner user ID",
                },
                "account_stage_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by account stage IDs",
                },
                "page": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "per_page": {
                    "type": "number",
                    "description": "Results per page, max 100 (e.g., 25, 50, 100)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)
        if not api_key:
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }

        body: dict = {
            "page": int(parameters.get("page", 1)),
            "per_page": min(int(parameters.get("per_page", 25)), 100),
        }
        q_keywords = parameters.get("q_keywords")
        if q_keywords:
            body["q_keywords"] = q_keywords
        owner_id = parameters.get("owner_id")
        if owner_id:
            body["owner_id"] = owner_id
        account_stage_ids = parameters.get("account_stage_ids")
        if account_stage_ids:
            body["account_stage_ids"] = account_stage_ids

        url = "https://api.apollo.io/api/v1/accounts/search"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
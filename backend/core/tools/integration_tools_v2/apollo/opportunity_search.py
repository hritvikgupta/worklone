from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloOpportunitySearchTool(BaseTool):
    name = "apollo_search_opportunities"
    description = "Search and list all deals/opportunities in your team's Apollo account"
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
        return (context or {}).get("APOLLO_API_KEY", "")

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "q_keywords": {
                    "type": "string",
                    "description": "Keywords to search for in opportunity names",
                },
                "account_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by specific account IDs (e.g., [\"acc_123\", \"acc_456\"])",
                },
                "stage_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by deal stage IDs",
                },
                "owner_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by opportunity owner IDs",
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
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }

        body: Dict[str, Any] = {
            "page": int(parameters.get("page") or 1),
            "per_page": min(int(parameters.get("per_page") or 25), 100),
        }
        q_keywords = parameters.get("q_keywords")
        if q_keywords:
            body["q_keywords"] = q_keywords
        account_ids = parameters.get("account_ids")
        if account_ids and len(account_ids) > 0:
            body["account_ids"] = account_ids
        stage_ids = parameters.get("stage_ids")
        if stage_ids and len(stage_ids) > 0:
            body["stage_ids"] = stage_ids
        owner_ids = parameters.get("owner_ids")
        if owner_ids and len(owner_ids) > 0:
            body["owner_ids"] = owner_ids

        url = "https://api.apollo.io/api/v1/opportunities/search"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HunterDiscoverTool(BaseTool):
    name = "hunter_discover"
    description = "Returns companies matching a set of criteria using Hunter.io AI-powered search."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _has_search_params(self, parameters: dict) -> bool:
        return bool(
            parameters.get("query") or
            parameters.get("domain") or
            parameters.get("headcount") or
            parameters.get("company_type") or
            parameters.get("technology")
        )

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="HUNTER_API_KEY",
                description="Hunter.io API Key",
                env_var="HUNTER_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query for companies",
                },
                "domain": {
                    "type": "string",
                    "description": "Company domain name to filter by (e.g., \"stripe.com\", \"company.io\")",
                },
                "headcount": {
                    "type": "string",
                    "description": "Company size filter (e.g., \"1-10\", \"11-50\")",
                },
                "company_type": {
                    "type": "string",
                    "description": "Type of organization",
                },
                "technology": {
                    "type": "string",
                    "description": "Technology used by companies",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("HUNTER_API_KEY") if context else None

        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="Hunter.io API key not configured.")

        if not self._has_search_params(parameters):
            return ToolResult(
                success=False,
                output="",
                error="At least one search parameter (query, domain, headcount, company_type, or technology) must be provided",
            )

        body: dict = {}
        if query := parameters.get("query"):
            body["query"] = query
        if domain := parameters.get("domain"):
            body["organization"] = {"domain": [domain]}
        if headcount := parameters.get("headcount"):
            body["headcount"] = headcount
        if company_type := parameters.get("company_type"):
            body["company_type"] = company_type
        if technology := parameters.get("technology"):
            body["technology"] = {"include": [technology]}

        headers = {
            "Content-Type": "application/json",
        }
        url = "https://api.hunter.io/v2/discover"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=body,
                    params={"api_key": api_key},
                )

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HunterDomainSearchTool(BaseTool):
    name = "hunter_domain_search"
    description = "Returns all the email addresses found using one given domain name, with sources."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

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

    async def _resolve_api_key(self, context: dict | None) -> str:
        return context.get("HUNTER_API_KEY", "") if context else ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": 'Domain name to search for email addresses (e.g., "stripe.com", "company.io")',
                },
                "limit": {
                    "type": "number",
                    "description": 'Maximum email addresses to return (e.g., 10, 25, 50). Default: 10',
                },
                "offset": {
                    "type": "number",
                    "description": 'Number of email addresses to skip for pagination (e.g., 0, 10, 20)',
                },
                "type": {
                    "type": "string",
                    "description": 'Filter for personal or generic emails (e.g., "personal", "generic", "all")',
                },
                "seniority": {
                    "type": "string",
                    "description": 'Filter by seniority level (e.g., "junior", "senior", "executive")',
                },
                "department": {
                    "type": "string",
                    "description": 'Filter by specific department (e.g., "sales", "marketing", "engineering", "hr")',
                },
            },
            "required": ["domain"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Hunter API key not configured.")

        headers = {
            "Content-Type": "application/json",
        }

        url = "https://api.hunter.io/v2/domain-search"

        query_params: Dict[str, str] = {
            "domain": parameters["domain"],
            "api_key": api_key,
        }

        limit = parameters.get("limit")
        if limit is not None:
            query_params["limit"] = str(limit)

        offset = parameters.get("offset")
        if offset is not None:
            query_params["offset"] = str(offset)

        type_param = parameters.get("type")
        if type_param and type_param != "all":
            query_params["type"] = type_param

        seniority = parameters.get("seniority")
        if seniority and seniority != "all":
            query_params["seniority"] = seniority

        department = parameters.get("department")
        if department:
            query_params["department"] = department

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
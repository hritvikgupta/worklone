from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloOrganizationSearchTool(BaseTool):
    name = "apollo_organization_search"
    description = "Search Apollo's database for companies using filters"
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

    def _resolve_api_key(self, context: dict | None) -> str:
        return context.get("APOLLO_API_KEY", "") if context else ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "organization_locations": {
                    "type": "array",
                    "description": "Company locations to search",
                },
                "organization_num_employees_ranges": {
                    "type": "array",
                    "description": "Employee count ranges (e.g., [\"1-10\", \"11-50\"])",
                },
                "q_organization_keyword_tags": {
                    "type": "array",
                    "description": "Industry or keyword tags",
                },
                "q_organization_name": {
                    "type": "string",
                    "description": "Organization name to search for (e.g., \"Acme\", \"TechCorp\")",
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
        api_key = self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }
        
        url = "https://api.apollo.io/api/v1/mixed_companies/search"
        
        body = {}
        page = parameters.get("page")
        page = int(page) if page is not None else 1
        body["page"] = page
        
        per_page = parameters.get("per_page")
        per_page = int(per_page) if per_page is not None else 25
        body["per_page"] = min(per_page, 100)
        
        organization_locations = parameters.get("organization_locations")
        if organization_locations:
            body["organization_locations"] = organization_locations
        
        organization_num_employees_ranges = parameters.get("organization_num_employees_ranges")
        if organization_num_employees_ranges:
            body["organization_num_employees_ranges"] = organization_num_employees_ranges
        
        q_organization_keyword_tags = parameters.get("q_organization_keyword_tags")
        if q_organization_keyword_tags:
            body["q_organization_keyword_tags"] = q_organization_keyword_tags
        
        q_organization_name = parameters.get("q_organization_name")
        if q_organization_name:
            body["q_organization_name"] = q_organization_name
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if 200 <= response.status_code < 300:
                    try:
                        resp_data = response.json()
                    except Exception:
                        return ToolResult(success=False, output=response.text, error="Invalid JSON response")
                    
                    pagination = resp_data.get("pagination", {})
                    output_data = {
                        "organizations": resp_data.get("organizations", []),
                        "page": pagination.get("page", 1),
                        "per_page": pagination.get("per_page", 25),
                        "total_entries": pagination.get("total_entries", 0),
                    }
                    return ToolResult(success=True, output=response.text, data=output_data)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Apollo API error: {response.status_code} - {response.text}",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
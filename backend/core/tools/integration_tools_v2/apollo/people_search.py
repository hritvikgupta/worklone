from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloPeopleSearchTool(BaseTool):
    name = "apollo_people_search"
    description = "Search Apollo's database for people using demographic filters"
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
                "person_titles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Job titles to search for (e.g., ["CEO", "VP of Sales"])',
                },
                "person_locations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Locations to search in (e.g., ["San Francisco, CA", "New York, NY"])',
                },
                "person_seniorities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Seniority levels (e.g., ["senior", "executive", "manager"])',
                },
                "organization_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Company names to search within',
                },
                "q_keywords": {
                    "type": "string",
                    "description": 'Keywords to search for',
                },
                "page": {
                    "type": "number",
                    "description": 'Page number for pagination, default 1 (e.g., 1, 2, 3)',
                },
                "per_page": {
                    "type": "number",
                    "description": 'Results per page, default 25, max 100 (e.g., 25, 50, 100)',
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
            "page": parameters.get("page", 1),
            "per_page": min(parameters.get("per_page", 25), 100),
        }
        
        for field in ["person_titles", "person_locations", "person_seniorities", "organization_names"]:
            field_value = parameters.get(field)
            if field_value and len(field_value) > 0:
                body[field] = field_value
        
        q_keywords = parameters.get("q_keywords")
        if q_keywords:
            body["q_keywords"] = q_keywords
        
        url = "https://api.apollo.io/api/v1/mixed_people/search"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
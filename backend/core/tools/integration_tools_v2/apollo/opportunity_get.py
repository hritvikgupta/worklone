from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloOpportunityGetTool(BaseTool):
    name = "apollo_opportunity_get"
    description = "Retrieve complete details of a specific deal/opportunity by ID"
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
        api_key = None
        if context:
            api_key = context.get("APOLLO_API_KEY")
        if not api_key:
            api_key = os.getenv("APOLLO_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ""
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "opportunity_id": {
                    "type": "string",
                    "description": "ID of the opportunity to retrieve (e.g., \"opp_abc123\")",
                },
            },
            "required": ["opportunity_id"],
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
        
        opportunity_id = parameters["opportunity_id"]
        url = f"https://api.apollo.io/api/v1/opportunities/{opportunity_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
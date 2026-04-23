from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloSequenceSearchTool(BaseTool):
    name = "apollo_sequence_search"
    description = "Search for sequences/campaigns in your team's Apollo account (master key required)"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "q_name": {
                    "type": "string",
                    "description": 'Search sequences by name (e.g., "Outbound Q1", "Follow-up")',
                },
                "active": {
                    "type": "boolean",
                    "description": 'Filter by active status (true for active sequences, false for inactive)',
                },
                "page": {
                    "type": "number",
                    "description": 'Page number for pagination (e.g., 1, 2, 3)',
                },
                "per_page": {
                    "type": "number",
                    "description": 'Results per page, max 100 (e.g., 25, 50, 100)',
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("APOLLO_API_KEY") if context else os.getenv("APOLLO_API_KEY")
        
        if self._is_placeholder_token(api_key or ""):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": api_key,
        }
        
        body = {
            "page": parameters.get("page") or 1,
            "per_page": min(parameters.get("per_page") or 25, 100),
        }
        q_name = parameters.get("q_name")
        if q_name:
            body["q_name"] = q_name
        if "active" in parameters:
            body["active"] = parameters["active"]
        
        url = "https://api.apollo.io/api/v1/emailer_campaigns/search"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
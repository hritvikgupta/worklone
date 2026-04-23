from typing import Any
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ApolloTaskSearchTool(BaseTool):
    name = "Apollo Search Tasks"
    description = "Search for tasks in Apollo"
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

    def _resolve_api_key(self, context: dict | None) -> str:
        return context.get("APOLLO_API_KEY", "") if context else ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": 'Filter by contact ID (e.g., "con_abc123")',
                },
                "account_id": {
                    "type": "string",
                    "description": 'Filter by account ID (e.g., "acc_abc123")',
                },
                "completed": {
                    "type": "boolean",
                    "description": "Filter by completion status",
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
        
        page = parameters.get("page", 1)
        per_page = min(parameters.get("per_page", 25), 100)
        body = {
            "page": page,
            "per_page": per_page,
        }
        contact_id = parameters.get("contact_id")
        if contact_id:
            body["contact_id"] = contact_id
        account_id = parameters.get("account_id")
        if account_id:
            body["account_id"] = account_id
        completed = parameters.get("completed")
        if completed is not None:
            body["completed"] = completed
        
        url = "https://api.apollo.io/api/v1/tasks/search"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
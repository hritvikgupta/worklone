from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class ZepGetThreadsTool(BaseTool):
    name = "Get Threads"
    description = "List all conversation threads"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ZEP_API_KEY",
                description="Your Zep API key",
                env_var="ZEP_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "zep",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("ZEP_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pageSize": {
                    "type": "number",
                    "description": "Number of threads to retrieve per page (e.g., 10, 25, 50)",
                },
                "pageNumber": {
                    "type": "number",
                    "description": "Page number for pagination (e.g., 1, 2, 3)",
                },
                "orderBy": {
                    "type": "string",
                    "description": "Field to order results by (created_at, updated_at, user_id, thread_id)",
                },
                "asc": {
                    "type": "boolean",
                    "description": "Order direction: true for ascending, false for descending",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Zep API key not configured.")
        
        headers = {
            "Authorization": f"Api-Key {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.getzep.com/api/v2/threads"
        params_dict = {
            "page_size": str(int(parameters.get("pageSize", 10))),
            "page_number": str(int(parameters.get("pageNumber", 1))),
        }
        if parameters.get("orderBy"):
            params_dict["order_by"] = parameters["orderBy"]
        if "asc" in parameters:
            params_dict["asc"] = str(parameters["asc"])
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params_dict)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
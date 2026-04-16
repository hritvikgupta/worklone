from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GammaListFoldersTool(BaseTool):
    name = "gamma_list_folders"
    description = "List available folders in your Gamma workspace. Returns folder IDs and names for organizing generated content."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GAMMA_API_KEY",
                description="Gamma API key",
                env_var="GAMMA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = (context or {}).get("GAMMA_API_KEY")
        if not api_key:
            api_key = os.getenv("GAMMA_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to filter folders by name (case-sensitive)",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of folders to return per page (max 50)",
                },
                "after": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response (nextCursor) to fetch the next page",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)

        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Gamma API key not configured.")

        headers = {
            "X-API-KEY": api_key,
        }

        url = "https://public-api.gamma.app/v1.0/folders"
        query_params = {k: v for k, v in parameters.items() if k in ("query", "limit", "after")}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
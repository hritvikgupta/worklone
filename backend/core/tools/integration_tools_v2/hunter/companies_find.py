from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class HunterCompaniesFindTool(BaseTool):
    name = "hunter_companies_find"
    description = "Enriches company data using domain name."
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
        api_key = (context or {}).get("HUNTER_API_KEY")
        if api_key is None:
            api_key = os.getenv("HUNTER_API_KEY")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": 'Domain to find company data for (e.g., "stripe.com", "company.io")',
                }
            },
            "required": ["domain"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
        }
        
        url = "https://api.hunter.io/v2/companies/find"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    params={
                        "api_key": api_key,
                        "domain": parameters.get("domain"),
                    },
                    headers=headers,
                )
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GammaCheckStatusTool(BaseTool):
    name = "gamma_check_status"
    description = "Check the status of a Gamma generation job. Returns the gamma URL when completed, or error details if failed."
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
        api_key = context.get("GAMMA_API_KEY") if context else ""
        if not api_key:
            api_key = os.getenv("GAMMA_API_KEY", "")
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "generationId": {
                    "type": "string",
                    "description": "The generation ID returned by the Generate or Generate from Template tool",
                },
            },
            "required": ["generationId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Gamma API key not configured.")
        
        headers = {
            "X-API-KEY": api_key,
        }
        
        generation_id = parameters.get("generationId")
        if not generation_id:
            return ToolResult(success=False, output="", error="Missing generationId parameter.")
        
        url = f"https://public-api.gamma.app/v1.0/generations/{generation_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import base64
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AshbyListCandidateTagsTool(BaseTool):
    name = "ashby_list_candidate_tags"
    description = "Lists all candidate tags configured in Ashby."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ashby_api_key",
                description="Ashby API Key",
                env_var="ASHBY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key: str | None = None
        if context is not None:
            api_key = context.get("ashby_api_key")
        if api_key is None:
            api_key = os.getenv("ASHBY_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ""
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = "https://api.ashbyhq.com/candidateTag.list"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json={})
                
                data = response.json()
                
                if not data.get("success", False):
                    error_msg = data.get("errorInfo", {}).get("message", "Failed to list candidate tags")
                    return ToolResult(success=False, output="", error=error_msg)
                    
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
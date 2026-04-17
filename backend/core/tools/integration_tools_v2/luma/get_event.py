from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LumaGetEventTool(BaseTool):
    name = "luma_get_event"
    description = "Retrieve details of a Luma event including name, time, location, hosts, and visibility settings."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Luma API key",
                env_var="LUMA_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = None
        if context:
            api_key = context.get("apiKey")
        if not api_key:
            api_key = os.getenv("LUMA_API_KEY")
        return api_key or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "eventId": {
                    "type": "string",
                    "description": "Event ID (starts with evt-)",
                },
            },
            "required": ["eventId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Luma API key not configured.")
        
        event_id = (parameters.get("eventId") or "").strip()
        if not event_id:
            return ToolResult(success=False, output="", error="Event ID is required.")
        
        url = f"https://public-api.luma.com/v1/event/get?id={event_id}"
        
        headers = {
            "x-luma-api-key": api_key,
            "Accept": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
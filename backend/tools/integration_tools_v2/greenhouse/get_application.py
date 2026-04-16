from typing import Any, Dict
import httpx
import base64
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class GreenhouseGetApplicationTool(BaseTool):
    name = "greenhouse_get_application"
    description = "Retrieves a specific application by ID with full details including source, stage, answers, and attachments"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="greenhouse_api_key",
                description="Greenhouse Harvest API key",
                env_var="GREENHOUSE_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> str:
        api_key = (context or {}).get("greenhouse_api_key")
        if api_key is None:
            api_key = os.getenv("GREENHOUSE_API_KEY")
        if self._is_placeholder_token(api_key or ""):
            return ""
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "applicationId": {
                    "type": "string",
                    "description": "The ID of the application to retrieve",
                },
            },
            "required": ["applicationId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Greenhouse API key not configured.")
        
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
            "Content-Type": "application/json",
        }
        
        application_id = parameters["applicationId"].strip()
        url = f"https://harvest.greenhouse.io/v1/applications/{application_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
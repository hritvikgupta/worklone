import httpx
import os
from typing import Any, Dict
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DevinCreateSessionTool(BaseTool):
    name = "create_session"
    description = "Create a new Devin session with a prompt. Devin will autonomously work on the task described in the prompt."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="devin_api_key",
                description="Devin API key (service user credential starting with cog_)",
                env_var="DEVIN_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = None
        if context is not None:
            token = context.get("devin_api_key")
            if token and not self._is_placeholder_token(token):
                return token
        token = os.getenv("DEVIN_API_KEY")
        if token and not self._is_placeholder_token(token):
            return token
        return ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The task prompt for Devin to work on",
                },
                "playbookId": {
                    "type": "string",
                    "description": "Optional playbook ID to guide the session",
                },
                "maxAcuLimit": {
                    "type": "number",
                    "description": "Maximum ACU limit for the session",
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tags for the session",
                },
            },
            "required": ["prompt"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Devin API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.devin.ai/v3/organizations/sessions"
        
        body = {
            "prompt": parameters["prompt"],
        }
        playbook_id = parameters.get("playbookId")
        if playbook_id:
            body["playbook_id"] = playbook_id
        max_acu_limit = parameters.get("maxAcuLimit")
        if max_acu_limit is not None:
            body["max_acu_limit"] = max_acu_limit
        tags_str = parameters.get("tags")
        if tags_str:
            body["tags"] = [t.strip() for t in tags_str.split(",")]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
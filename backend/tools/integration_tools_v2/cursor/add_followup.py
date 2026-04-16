from typing import Any, Dict
import httpx
import base64
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class CursorAddFollowupTool(BaseTool):
    name = "cursor_add_followup"
    description = "Add a follow-up instruction to an existing cloud agent. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="CURSOR_API_KEY",
                description="Cursor API key",
                env_var="CURSOR_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "agentId": {
                    "type": "string",
                    "description": "Unique identifier for the cloud agent (e.g., bc_abc123)",
                },
                "followupPromptText": {
                    "type": "string",
                    "description": "The follow-up instruction text for the agent",
                },
                "promptImages": {
                    "type": "string",
                    "description": "JSON array of image objects with base64 data and dimensions (max 5)",
                },
            },
            "required": ["agentId", "followupPromptText"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("CURSOR_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Cursor API key not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{api_key}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = f"https://api.cursor.com/v0/agents/{parameters['agentId'].strip()}/followup"
        
        body = {
            "prompt": {
                "text": parameters["followupPromptText"],
            },
        }
        
        prompt_images_str = parameters.get("promptImages")
        if prompt_images_str:
            try:
                body["prompt"]["images"] = json.loads(prompt_images_str)
            except json.JSONDecodeError:
                body["prompt"]["images"] = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
import os
import httpx
from typing import Any, Dict
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class DevinSendMessageTool(BaseTool):
    name = "send_message"
    description = "Send a message to a Devin session. If the session is suspended, it will be automatically resumed. Returns the updated session state."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="DEVIN_API_KEY",
                description="Devin API key (service user credential starting with cog_)",
                env_var="DEVIN_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = context.get("DEVIN_API_KEY") if context else None
        if token is None:
            token = os.getenv("DEVIN_API_KEY")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "sessionId": {
                    "type": "string",
                    "description": "The session ID to send the message to",
                },
                "message": {
                    "type": "string",
                    "description": "The message to send to Devin",
                },
            },
            "required": ["sessionId", "message"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Devin API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        session_id = parameters["sessionId"]
        message = parameters["message"]
        url = f"https://api.devin.ai/v3/organizations/sessions/{session_id}/messages"
        
        json_body = {
            "message": message,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
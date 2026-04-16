from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class ZepAddUserTool(BaseTool):
    name = "zep_add_user"
    description = "Create a new user in Zep"
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

    def _resolve_api_key(self, context: dict | None) -> str | None:
        candidates = []
        if context and "ZEP_API_KEY" in context:
            candidates.append(context["ZEP_API_KEY"])
        env_key = os.getenv("ZEP_API_KEY")
        if env_key:
            candidates.append(env_key)
        for cand in candidates:
            if not self._is_placeholder_token(cand):
                return cand
        return None

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "userId": {
                    "type": "string",
                    "description": 'Unique identifier for the user (e.g., "user_123")',
                },
                "email": {
                    "type": "string",
                    "description": "User email address",
                },
                "firstName": {
                    "type": "string",
                    "description": "User first name",
                },
                "lastName": {
                    "type": "string",
                    "description": "User last name",
                },
                "metadata": {
                    "type": "object",
                    "description": 'Additional metadata as JSON object (e.g., {"key": "value"})',
                },
            },
            "required": ["userId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._resolve_api_key(context)
        
        if not api_key:
            return ToolResult(success=False, output="", error="Zep API key not configured.")
        
        headers = {
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.getzep.com/api/v2/users"
        
        body: Dict[str, Any] = {
            "user_id": parameters["userId"],
        }
        email = parameters.get("email")
        if email:
            body["email"] = email
        first_name = parameters.get("firstName")
        if first_name:
            body["first_name"] = first_name
        last_name = parameters.get("lastName")
        if last_name:
            body["last_name"] = last_name
        metadata = parameters.get("metadata")
        if metadata:
            body["metadata"] = metadata
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
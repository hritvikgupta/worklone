from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AshbyCreateCandidateTool(BaseTool):
    name = "ashby_create_candidate"
    description = "Creates a new candidate record in Ashby."
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "ashby",
            context=context,
            context_token_keys=("ashby_api_key",),
            env_token_keys=("ASHBY_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The candidate full name",
                },
                "email": {
                    "type": "string",
                    "description": "Primary email address for the candidate",
                },
                "phoneNumber": {
                    "type": "string",
                    "description": "Primary phone number for the candidate",
                },
                "linkedInUrl": {
                    "type": "string",
                    "description": "LinkedIn profile URL",
                },
                "githubUrl": {
                    "type": "string",
                    "description": "GitHub profile URL",
                },
                "sourceId": {
                    "type": "string",
                    "description": "UUID of the source to attribute the candidate to",
                },
            },
            "required": ["name", "email"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{access_token}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        body = {
            "name": parameters["name"],
            "email": parameters["email"],
        }
        for field in ["phoneNumber", "linkedInUrl", "githubUrl", "sourceId"]:
            if field in parameters and parameters[field]:
                body[field] = parameters[field]
        
        url = "https://api.ashbyhq.com/candidate.create"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                try:
                    data = response.json()
                except Exception:
                    return ToolResult(success=False, output="", error="Invalid JSON response")
                
                if not data.get("success", False):
                    error_info = data.get("errorInfo", {})
                    error_msg = error_info.get("message", "Failed to create candidate") if isinstance(error_info, dict) else str(data)
                    return ToolResult(success=False, output="", error=error_msg)
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
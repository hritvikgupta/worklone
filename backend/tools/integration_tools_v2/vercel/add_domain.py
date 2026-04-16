from typing import Dict
import httpx
from urllib.parse import urlencode
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelAddDomainTool(BaseTool):
    name = "vercel_add_domain"
    description = "Add a new domain to a Vercel account or team"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="VERCEL_API_KEY",
                description="Vercel Access Token",
                env_var="VERCEL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    def _get_api_key(self, context: dict | None) -> str:
        if not context:
            return ""
        api_key = context.get("VERCEL_API_KEY", "")
        return api_key.strip()

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The domain name to add",
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["name"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = self._get_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        qs_params: dict[str, str] = {}
        team_id = parameters.get("teamId")
        if team_id:
            qs_params["teamId"] = str(team_id).strip()
        url = "https://api.vercel.com/v7/domains"
        if qs_params:
            url += "?" + urlencode(qs_params)
        
        body = {
            "method": "add",
            "name": str(parameters["name"]).strip(),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import os
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelListEdgeConfigsTool(BaseTool):
    name = "Vercel List Edge Configs"
    description = "List all Edge Config stores for a team"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="vercel_api_key",
                description="Vercel Access Token",
                env_var="VERCEL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        token = context.get("vercel_api_key") if context else None
        if self._is_placeholder_token(token):
            token = os.getenv("VERCEL_API_KEY")
        return token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        team_id = parameters.get("teamId")
        url = "https://api.vercel.com/v1/edge-config"
        if team_id:
            url += f"?teamId={team_id.strip()}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    items = data if isinstance(data, list) else data.get("edgeConfigs", [])
                    edge_configs = []
                    for ec in items:
                        edge_configs.append({
                            "id": ec.get("id"),
                            "slug": ec.get("slug"),
                            "ownerId": ec.get("ownerId"),
                            "digest": ec.get("digest"),
                            "createdAt": ec.get("createdAt"),
                            "updatedAt": ec.get("updatedAt"),
                            "itemCount": ec.get("itemCount", 0),
                            "sizeInBytes": ec.get("sizeInBytes", 0),
                        })
                    transformed = {
                        "edgeConfigs": edge_configs,
                        "count": len(edge_configs),
                    }
                    return ToolResult(success=True, output=response.text, data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
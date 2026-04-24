from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class VercelUpdateEdgeConfigItemsTool(BaseTool):
    name = "vercel_update_edge_config_items"
    description = "Create, update, upsert, or delete items in an Edge Config store"
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

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "vercel",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("VERCEL_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "edgeConfigId": {
                    "type": "string",
                    "description": "Edge Config ID to update items in",
                },
                "items": {
                    "type": "array",
                    "description": 'Array of operations: [{operation: "create"|"update"|"upsert"|"delete", key: string, value?: any}]',
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request",
                },
            },
            "required": ["edgeConfigId", "items"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        edge_config_id = parameters["edgeConfigId"].strip()
        items = parameters["items"]
        team_id = parameters.get("teamId")
        url = f"https://api.vercel.com/v1/edge-config/{edge_config_id}/items"
        if team_id:
            team_id = team_id.strip()
            url += f"?teamId={team_id}"
        
        body = {"items": items}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
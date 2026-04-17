from typing import Any, Dict
import httpx
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class VercelListWebhooksTool(BaseTool):
    name = "vercel_list_webhooks"
    description = "List webhooks for a Vercel project or team"
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
        return context.get("VERCEL_API_KEY") if context else ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "projectId": {
                    "type": "string",
                    "description": "Filter webhooks by project ID"
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to scope the request"
                }
            },
            "required": []
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        query_params = {}
        if project_id := parameters.get("projectId"):
            query_params["projectId"] = str(project_id).strip()
        if team_id := parameters.get("teamId"):
            query_params["teamId"] = str(team_id).strip()
        
        url = "https://api.vercel.com/v1/webhooks"
        if query_params:
            url += "?" + urlencode(query_params)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        raw_data = response.json()
                        webhooks = []
                        if isinstance(raw_data, list):
                            for w in raw_data:
                                webhooks.append({
                                    "id": w.get("id"),
                                    "url": w.get("url"),
                                    "events": w.get("events", []),
                                    "ownerId": w.get("ownerId"),
                                    "projectIds": w.get("projectIds", []),
                                    "createdAt": w.get("createdAt"),
                                    "updatedAt": w.get("updatedAt"),
                                })
                        result = {
                            "webhooks": webhooks,
                            "count": len(webhooks)
                        }
                        return ToolResult(success=True, output=str(result), data=result)
                    except Exception as parse_e:
                        return ToolResult(success=False, output="", error=f"Failed to parse response: {str(parse_e)}")
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
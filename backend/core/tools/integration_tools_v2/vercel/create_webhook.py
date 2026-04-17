from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class VercelCreateWebhookTool(BaseTool):
    name = "vercel_create_webhook"
    description = "Create a new webhook for a Vercel team"
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
                "url": {
                    "type": "string",
                    "description": "Webhook URL (must be https)"
                },
                "events": {
                    "type": "string",
                    "description": "Comma-separated event names to subscribe to"
                },
                "projectIds": {
                    "type": "string",
                    "description": "Comma-separated project IDs to scope the webhook to"
                },
                "teamId": {
                    "type": "string",
                    "description": "Team ID to create the webhook for"
                }
            },
            "required": ["url", "events", "teamId"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        team_id = parameters.get("teamId", "").strip()
        url = "https://api.vercel.com/v1/webhooks"
        if team_id:
            url += f"?teamId={team_id}"
        
        body = {
            "url": parameters["url"].strip(),
            "events": [e.strip() for e in parameters["events"].split(",")],
        }
        project_ids_str = parameters.get("projectIds", "").strip()
        if project_ids_str:
            body["projectIds"] = [p.strip() for p in project_ids_str.split(",")]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection

class IncidentioActionsListTool(BaseTool):
    name = "incidentio_actions_list"
    description = "List actions from incident.io. Optionally filter by incident ID."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INCIDENTIO_ACCESS_TOKEN",
                description="incident.io API Key",
                env_var="INCIDENTIO_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "incidentio",
            context=context,
            context_token_keys=("provider_token",},
            env_token_keys=("INCIDENTIO_ACCESS_TOKEN",},
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "Filter actions by incident ID (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        base_url = "https://api.incident.io/v2/actions"
        query_params: Dict[str, str] = {}
        incident_id = parameters.get("incident_id")
        if incident_id:
            query_params["incident_id"] = incident_id
        url = base_url
        if query_params:
            url += "?" + urlencode(query_params)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
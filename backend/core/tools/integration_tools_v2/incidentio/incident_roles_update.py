from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IncidentioRolesUpdateTool(BaseTool):
    name = "update_incident_role"
    description = "Update an existing incident role in incident.io"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INCIDENTIO_API_KEY",
                description="incident.io API Key",
                env_var="INCIDENTIO_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "incidentio",
            context=context,
            context_token_keys=("api_key",),
            env_token_keys=("INCIDENTIO_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The ID of the incident role to update (e.g., \"01FCNDV6P870EA6S7TK1DSYDG0\")",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the incident role (e.g., \"Incident Commander\")",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the incident role",
                },
                "instructions": {
                    "type": "string",
                    "description": "Instructions for the incident role",
                },
                "shortform": {
                    "type": "string",
                    "description": "Short form abbreviation for the role",
                },
            },
            "required": ["id", "name", "description", "instructions", "shortform"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.incident.io/v2/incident_roles/{parameters['id']}"
        body = {
            "name": parameters["name"],
            "description": parameters["description"],
            "instructions": parameters["instructions"],
            "shortform": parameters["shortform"],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
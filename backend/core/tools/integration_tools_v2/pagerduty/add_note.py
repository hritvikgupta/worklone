from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PagerDutyAddNoteTool(BaseTool):
    name = "pagerduty_add_note"
    description = "Add a note to an existing PagerDuty incident."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PAGERDUTY_API_KEY",
                description="PagerDuty REST API Key",
                env_var="PAGERDUTY_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pagerduty",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("PAGERDUTY_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "fromEmail": {
                    "type": "string",
                    "description": "Email address of a valid PagerDuty user",
                },
                "incidentId": {
                    "type": "string",
                    "description": "ID of the incident to add the note to",
                },
                "content": {
                    "type": "string",
                    "description": "Note content text",
                },
            },
            "required": ["fromEmail", "incidentId", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Token token={access_token}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
            "From": parameters["fromEmail"],
        }
        
        url = f"https://api.pagerduty.com/incidents/{parameters['incidentId'].strip()}/notes"
        body = {
            "note": {
                "content": parameters["content"],
            },
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
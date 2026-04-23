from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AshbyChangeApplicationStageTool(BaseTool):
    name = "ashby_change_application_stage"
    description = "Moves an application to a different interview stage. Requires an archive reason when moving to an Archived stage."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ASHBY_API_KEY",
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
            context_token_keys=("apiKey",),
            env_token_keys=("ASHBY_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "applicationId": {
                    "type": "string",
                    "description": "The UUID of the application to update the stage of",
                },
                "interviewStageId": {
                    "type": "string",
                    "description": "The UUID of the interview stage to move the application to",
                },
                "archiveReasonId": {
                    "type": "string",
                    "description": "Archive reason UUID. Required when moving to an Archived stage, ignored otherwise",
                },
            },
            "required": ["applicationId", "interviewStageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(f'{access_token}:'.encode('utf-8')).decode('utf-8')}",
        }
        
        url = "https://api.ashbyhq.com/application.changeStage"
        
        body = {
            "applicationId": parameters["applicationId"],
            "interviewStageId": parameters["interviewStageId"],
        }
        if "archiveReasonId" in parameters:
            body["archiveReasonId"] = parameters["archiveReasonId"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
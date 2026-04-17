from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackUpdateViewTool(BaseTool):
    name = "slack_update_view"
    description = "Update an existing modal view in Slack. Identify the view by view_id or external_id, and provide the updated view payload."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_TOKEN",
                description="Access token or bot token for Slack API",
                env_var="SLACK_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("accessToken", "botToken"),
            env_token_keys=("SLACK_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "viewId": {
                    "type": "string",
                    "description": "Unique identifier of the view to update. Either viewId or externalId is required",
                },
                "externalId": {
                    "type": "string",
                    "description": "Developer-set unique identifier of the view to update (max 255 chars). Either viewId or externalId is required",
                },
                "hash": {
                    "type": "string",
                    "description": "View state hash to protect against race conditions. Obtained from a previous views response",
                },
                "view": {
                    "type": "object",
                    "description": "A view payload object defining the updated modal. Must include type (\"modal\"), title, and blocks array. Use identical block_id and action_id values to preserve input data",
                },
            },
            "required": ["view"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/views.update"
        
        body = {"view": parameters.get("view")}
        if parameters.get("viewId"):
            body["view_id"] = parameters["viewId"].strip()
        if parameters.get("externalId"):
            body["external_id"] = parameters["externalId"].strip()
        if parameters.get("hash"):
            body["hash"] = parameters["hash"].strip()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if not data.get("ok", False):
                    return ToolResult(success=False, output="", error=str(data))
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
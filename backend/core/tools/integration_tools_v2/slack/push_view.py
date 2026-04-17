from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class SlackPushViewTool(BaseTool):
    name = "slack_push_view"
    description = "Push a new view onto an existing modal stack in Slack. Limited to 2 additional views after the initial modal is opened."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="SLACK_ACCESS_TOKEN",
                description="OAuth access token or bot token for Slack API",
                env_var="SLACK_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "slack",
            context=context,
            context_token_keys=("accessToken", "botToken"),
            env_token_keys=("SLACK_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "triggerId": {
                    "type": "string",
                    "description": "Exchange a trigger to post to the user. Obtained from an interaction payload (e.g., button click within an existing modal)",
                },
                "interactivityPointer": {
                    "type": "string",
                    "description": "Alternative to trigger_id for posting to user",
                },
                "view": {
                    "type": "object",
                    "description": "A view payload object defining the modal to push. Must include type (\"modal\"), title, and blocks array",
                },
            },
            "required": ["triggerId", "view"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://slack.com/api/views.push"
        
        body: dict = {"view": parameters.get("view")}
        trigger_id = (parameters.get("triggerId") or "").strip()
        if trigger_id:
            body["trigger_id"] = trigger_id
        interactivity_pointer = (parameters.get("interactivityPointer") or "").strip()
        if interactivity_pointer:
            body["interactivity_pointer"] = interactivity_pointer
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                if not data.get("ok"):
                    error = data.get("error", "Slack API error")
                    return ToolResult(success=False, output="", error=error)
                
                return ToolResult(success=True, output=response.text, data=data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
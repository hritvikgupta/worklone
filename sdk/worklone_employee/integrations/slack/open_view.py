from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class SlackOpenViewTool(BaseTool):
    name = "slack_open_view"
    description = "Open a modal view in Slack using a trigger_id from an interaction payload. Used to display forms, confirmations, and other interactive modals."
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
                    "description": "Exchange a trigger to post to the user. Obtained from an interaction payload (e.g., slash command, button click)",
                },
                "interactivityPointer": {
                    "type": "string",
                    "description": "Alternative to trigger_id for posting to user",
                },
                "view": {
                    "type": "object",
                    "description": "A view payload object defining the modal. Must include type (\"modal\"), title, and blocks array",
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
        
        url = "https://slack.com/api/views.open"
        
        body = {"view": parameters["view"]}
        trigger_id = (parameters.get("triggerId") or "").strip()
        if trigger_id:
            body["trigger_id"] = trigger_id
        interactivity_pointer = (parameters.get("interactivityPointer") or "").strip()
        if interactivity_pointer:
            body["interactivity_pointer"] = interactivity_pointer
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                data = response.json()
                
                if data.get("ok"):
                    view = data.get("view", {})
                    output_view = {
                        "id": view.get("id"),
                        "team_id": view.get("team_id"),
                        "type": view.get("type"),
                        "title": view.get("title"),
                        "submit": view.get("submit"),
                        "close": view.get("close"),
                        "blocks": view.get("blocks", []),
                        "private_metadata": view.get("private_metadata"),
                        "callback_id": view.get("callback_id"),
                        "external_id": view.get("external_id"),
                        "state": view.get("state"),
                        "hash": view.get("hash"),
                        "clear_on_close": view.get("clear_on_close", False),
                        "notify_on_close": view.get("notify_on_close", False),
                        "root_view_id": view.get("root_view_id"),
                        "previous_view_id": view.get("previous_view_id"),
                        "app_id": view.get("app_id"),
                        "bot_id": view.get("bot_id"),
                    }
                    return ToolResult(success=True, output="Modal view opened successfully.", data={"view": output_view})
                else:
                    error = data.get("error")
                    if error == "expired_trigger_id":
                        err_msg = "The trigger_id has expired. Trigger IDs are only valid for 3 seconds after the interaction."
                    elif error == "invalid_trigger_id":
                        err_msg = "Invalid trigger_id. Ensure you are using a trigger_id from a valid interaction payload."
                    elif error == "exchanged_trigger_id":
                        err_msg = "This trigger_id has already been used. Each trigger_id can only be used once."
                    elif error == "view_too_large":
                        err_msg = "The view payload is too large. Reduce the number of blocks or content."
                    elif error == "duplicate_external_id":
                        err_msg = "A view with this external_id already exists. Use a unique external_id per workspace."
                    elif error == "invalid_arguments":
                        messages = data.get("response_metadata", {}).get("messages", [])
                        err_msg = f"Invalid view arguments: {', '.join(messages) if messages else error}"
                    elif error == "missing_scope":
                        err_msg = "Missing required permissions. Please reconnect your Slack account with the necessary scopes."
                    elif error in ["invalid_auth", "not_authed", "token_expired"]:
                        err_msg = "Invalid authentication. Please check your Slack credentials."
                    else:
                        err_msg = error or "Failed to open view in Slack"
                    return ToolResult(success=False, output="", error=err_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
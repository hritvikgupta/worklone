from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveUpdateActivityTool(BaseTool):
    name = "pipedrive_update_activity"
    description = "Update an existing activity (task) in Pipedrive"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PIPEDRIVE_ACCESS_TOKEN",
                description="The access token for the Pipedrive API",
                env_var="PIPEDRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def _build_body(self, parameters: dict) -> dict:
        body: dict[str, Any] = {}
        subject = parameters.get("subject")
        if subject:
            body["subject"] = subject
        due_date = parameters.get("due_date")
        if due_date:
            body["due_date"] = due_date
        due_time = parameters.get("due_time")
        if due_time:
            body["due_time"] = due_time
        duration = parameters.get("duration")
        if duration:
            body["duration"] = duration
        done = parameters.get("done")
        if done is not None:
            body["done"] = 1 if done == "1" else 0
        note = parameters.get("note")
        if note:
            body["note"] = note
        return body

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "string",
                    "description": "The ID of the activity to update (e.g., \"12345\")",
                },
                "subject": {
                    "type": "string",
                    "description": "New subject/title for the activity (e.g., \"Updated meeting with client\")",
                },
                "due_date": {
                    "type": "string",
                    "description": "New due date in YYYY-MM-DD format (e.g., \"2025-03-20\")",
                },
                "due_time": {
                    "type": "string",
                    "description": "New due time in HH:MM format (e.g., \"15:00\")",
                },
                "duration": {
                    "type": "string",
                    "description": "New duration in HH:MM format (e.g., \"00:30\" for 30 minutes)",
                },
                "done": {
                    "type": "string",
                    "description": "Mark as done: 0 for not done, 1 for done",
                },
                "note": {
                    "type": "string",
                    "description": "New notes for the activity",
                },
            },
            "required": ["activity_id"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        activity_id = parameters["activity_id"]
        url = f"https://api.pipedrive.com/v1/activities/{activity_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        body = self._build_body(parameters)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
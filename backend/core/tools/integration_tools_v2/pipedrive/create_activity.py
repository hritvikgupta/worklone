from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class PipedriveCreateActivityTool(BaseTool):
    name = "pipedrive_create_activity"
    description = "Create a new activity (task) in Pipedrive"
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
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "pipedrive",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("PIPEDRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "The subject/title of the activity (e.g., \"Follow up call with John\")",
                },
                "type": {
                    "type": "string",
                    "description": "Activity type: call, meeting, task, deadline, email, lunch",
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format (e.g., \"2025-03-15\")",
                },
                "due_time": {
                    "type": "string",
                    "description": "Due time in HH:MM format (e.g., \"14:30\")",
                },
                "duration": {
                    "type": "string",
                    "description": "Duration in HH:MM format (e.g., \"01:00\" for 1 hour)",
                },
                "deal_id": {
                    "type": "string",
                    "description": "ID of the deal to associate with (e.g., \"123\")",
                },
                "person_id": {
                    "type": "string",
                    "description": "ID of the person to associate with (e.g., \"456\")",
                },
                "org_id": {
                    "type": "string",
                    "description": "ID of the organization to associate with (e.g., \"789\")",
                },
                "note": {
                    "type": "string",
                    "description": "Notes for the activity",
                },
            },
            "required": ["subject", "type", "due_date"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        body: Dict[str, Any] = {
            "subject": parameters["subject"],
            "type": parameters["type"],
            "due_date": parameters["due_date"],
        }
        if parameters.get("due_time"):
            body["due_time"] = parameters["due_time"]
        if parameters.get("duration"):
            body["duration"] = parameters["duration"]
        if parameters.get("deal_id"):
            body["deal_id"] = int(parameters["deal_id"])
        if parameters.get("person_id"):
            body["person_id"] = int(parameters["person_id"])
        if parameters.get("org_id"):
            body["org_id"] = int(parameters["org_id"])
        if parameters.get("note"):
            body["note"] = parameters["note"]
        
        url = "https://api.pipedrive.com/v1/activities"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class IntercomAssignConversationTool(BaseTool):
    name = "Assign Conversation in Intercom"
    description = "Assign a conversation to an admin or team in Intercom"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="INTERCOM_ACCESS_TOKEN",
                description="Intercom API access token",
                env_var="INTERCOM_ACCESS_TOKEN",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "intercom",
            context=context,
            context_token_keys=("intercom_token",),
            env_token_keys=("INTERCOM_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "conversationId": {
                    "type": "string",
                    "description": "The ID of the conversation to assign",
                },
                "admin_id": {
                    "type": "string",
                    "description": "The ID of the admin performing the assignment",
                },
                "assignee_id": {
                    "type": "string",
                    "description": 'The ID of the admin or team to assign the conversation to. Set to "0" to unassign.',
                },
                "body": {
                    "type": "string",
                    "description": 'Optional message to add when assigning (e.g., "Passing to the support team")',
                },
            },
            "required": ["conversationId", "admin_id", "assignee_id"],
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Intercom-Version": "2.14",
        }
        
        conversation_id = parameters["conversationId"]
        url = f"https://api.intercom.io/conversations/{conversation_id}/parts"
        
        body = {
            "message_type": "assignment",
            "type": "admin",
            "admin_id": parameters["admin_id"],
            "assignee_id": parameters["assignee_id"],
        }
        if body_param := parameters.get("body"):
            body["body"] = body_param
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
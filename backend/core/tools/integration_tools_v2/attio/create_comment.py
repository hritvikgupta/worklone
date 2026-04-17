from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class AttioCreateCommentTool(BaseTool):
    name = "attio_create_comment"
    description = "Create a comment on a list entry in Attio"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="ATTIO_ACCESS_TOKEN",
                description="Attio OAuth access token",
                env_var="ATTIO_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "attio",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("ATTIO_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The comment content",
                },
                "format": {
                    "type": "string",
                    "description": "Content format: plaintext or markdown (default plaintext)",
                },
                "authorType": {
                    "type": "string",
                    "description": "Author type (e.g. workspace-member)",
                },
                "authorId": {
                    "type": "string",
                    "description": "Author workspace member ID",
                },
                "list": {
                    "type": "string",
                    "description": "The list ID or slug the entry belongs to",
                },
                "entryId": {
                    "type": "string",
                    "description": "The entry ID to comment on",
                },
                "threadId": {
                    "type": "string",
                    "description": "Thread ID to reply to (omit to start a new thread)",
                },
                "createdAt": {
                    "type": "string",
                    "description": "Backdate the comment (ISO 8601 format)",
                },
            },
            "required": ["content", "authorType", "authorId", "list", "entryId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        data: Dict[str, Any] = {
            "format": parameters.get("format", "plaintext"),
            "content": parameters["content"],
            "author": {
                "type": parameters["authorType"],
                "id": parameters["authorId"],
            },
            "entry": {
                "list": parameters["list"],
                "entry_id": parameters["entryId"],
            },
        }
        if "threadId" in parameters:
            data["thread_id"] = parameters["threadId"]
        if "createdAt" in parameters:
            data["created_at"] = parameters["createdAt"]
        body = {"data": data}
        url = "https://api.attio.com/v2/comments"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
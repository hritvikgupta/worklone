from typing import Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearDeleteAttachmentTool(BaseTool):
    name = "linear_delete_attachment"
    description = "Delete an attachment from Linear"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="LINEAR_ACCESS_TOKEN",
                description="Access token",
                env_var="LINEAR_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "linear",
            context=context,
            context_token_keys=("linear_token",),
            env_token_keys=("LINEAR_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "attachmentId": {
                    "type": "string",
                    "description": "Attachment ID to delete",
                },
            },
            "required": ["attachmentId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.linear.app/graphql"
        body = {
            "query": """
                mutation DeleteAttachment($id: String!) {
                  attachmentDelete(id: $id) {
                    success
                  }
                }
            """,
            "variables": {
                "id": parameters["attachmentId"],
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code not in [200, 201, 204]:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if "errors" in data and data["errors"]:
                    error_msg = data["errors"][0].get("message", "Failed to delete attachment")
                    return ToolResult(success=False, output="", error=error_msg)
                
                success = data["data"]["attachmentDelete"]["success"]
                output_data = {"success": success}
                
                return ToolResult(
                    success=success,
                    output=str(output_data),
                    data=data,
                )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LinearUpdateAttachmentTool(BaseTool):
    name = "linear_update_attachment"
    description = "Update an attachment metadata in Linear"
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
                    "description": "Attachment ID to update",
                },
                "title": {
                    "type": "string",
                    "description": "New attachment title",
                },
                "subtitle": {
                    "type": "string",
                    "description": "New attachment subtitle",
                },
            },
            "required": ["attachmentId", "title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        input_dict: Dict[str, Any] = {
            "title": parameters["title"],
        }
        subtitle = parameters.get("subtitle")
        if subtitle is not None and subtitle != "":
            input_dict["subtitle"] = subtitle
        
        body = {
            "query": """
                mutation UpdateAttachment($id: String!, $input: AttachmentUpdateInput!) {
                  attachmentUpdate(id: $id, input: $input) {
                    success
                    attachment {
                      id
                      title
                      subtitle
                      url
                      createdAt
                      updatedAt
                    }
                  }
                }
            """,
            "variables": {
                "id": parameters["attachmentId"],
                "input": input_dict,
            },
        }
        
        url = "https://api.linear.app/graphql"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                if data.get("errors"):
                    error_msg = data["errors"][0].get("message", "Failed to update attachment") if data["errors"] else "Unknown GraphQL error"
                    return ToolResult(success=False, output="", error=error_msg)
                
                result = data.get("data", {}).get("attachmentUpdate", {})
                if not result.get("success", False):
                    return ToolResult(success=False, output="", error="Attachment update was not successful")
                
                attachment_data = {"attachment": result.get("attachment", {})}
                return ToolResult(success=True, output=response.text, data=attachment_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
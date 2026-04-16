from typing import Any, Dict
import httpx
import base64
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressCreateCommentTool(BaseTool):
    name = "wordpress_create_comment"
    description = "Create a new comment on a WordPress.com post"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="WORDPRESS_ACCESS_TOKEN",
                description="Access token",
                env_var="WORDPRESS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "wordpress",
            context=context,
            context_token_keys=("wordpress_token",),
            env_token_keys=("WORDPRESS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "siteId": {
                    "type": "string",
                    "description": "WordPress.com site ID or domain (e.g., 12345678 or mysite.wordpress.com)"
                },
                "postId": {
                    "type": "number",
                    "description": "The ID of the post to comment on"
                },
                "content": {
                    "type": "string",
                    "description": "Comment content"
                },
                "parent": {
                    "type": "number",
                    "description": "Parent comment ID for replies"
                },
                "authorName": {
                    "type": "string",
                    "description": "Comment author display name"
                },
                "authorEmail": {
                    "type": "string",
                    "description": "Comment author email"
                },
                "authorUrl": {
                    "type": "string",
                    "description": "Comment author URL"
                }
            },
            "required": ["siteId", "postId", "content"]
        }

    async def execute(self, parameters: dict, context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://public-api.wordpress.com/rest/v1.1/sites/{parameters['siteId']}/comments"
        
        body = {
            "post": parameters["postId"],
            "content": parameters["content"],
        }
        param_mappings = [
            ("parent", "parent"),
            ("authorName", "author_name"),
            ("authorEmail", "author_email"),
            ("authorUrl", "author_url"),
        ]
        for param_name, body_key in param_mappings:
            if param_name in parameters:
                body[body_key] = parameters[param_name]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import base64
import mimetypes
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class WordPressUploadMediaTool(BaseTool):
    name = "wordpress_upload_media"
    description = "Upload a media file (image, video, document) to WordPress.com"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="WORDPRESS_ACCESS_TOKEN",
                description="WordPress.com access token",
                env_var="WORDPRESS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "wordpress",
            context=context,
            context_token_keys=("accessToken", "access_token", "wordpress_token"),
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
                    "description": "WordPress.com site ID or domain (e.g., 12345678 or mysite.wordpress.com)",
                },
                "file": {
                    "type": "string",
                    "description": "File to upload (UserFile object)",
                },
                "filename": {
                    "type": "string",
                    "description": "Optional filename override (e.g., image.jpg)",
                },
                "title": {
                    "type": "string",
                    "description": "Media title",
                },
                "caption": {
                    "type": "string",
                    "description": "Media caption",
                },
                "altText": {
                    "type": "string",
                    "description": "Alternative text for accessibility",
                },
                "description": {
                    "type": "string",
                    "description": "Media description",
                },
            },
            "required": ["siteId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        site_id = parameters.get("siteId")
        if not site_id:
            return ToolResult(success=False, output="", error="siteId is required.")
        
        url = f"https://public-api.wordpress.com/rest/v1/sites/{site_id}/media/new"
        
        file_b64 = parameters.get("file")
        if not file_b64:
            return ToolResult(success=False, output="", error="File is required.")
        
        try:
            file_bytes = base64.b64decode(file_b64)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Invalid base64 file content: {str(e)}")
        
        filename = parameters.get("filename", "media")
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        
        title = parameters.get("title")
        caption = parameters.get("caption")
        alt_text = parameters.get("altText")
        description = parameters.get("description")
        
        data: Dict[str, str] = {}
        if title:
            data["title"] = title
        if caption:
            data["caption"] = caption
        if alt_text:
            data["alt"] = alt_text
        if description:
            data["description"] = description
        
        files = {
            "file": (filename, file_bytes, mime_type),
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, files=files, data=data)
                
                if response.status_code in [200, 201]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
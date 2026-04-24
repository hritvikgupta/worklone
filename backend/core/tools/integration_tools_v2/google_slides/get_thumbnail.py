from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesGetThumbnailTool(BaseTool):
    name = "google_slides_get_thumbnail"
    description = "Generate a thumbnail image of a specific slide in a Google Slides presentation"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Access token for the Google Slides API",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection("google_slides",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_DRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "presentationId": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "pageObjectId": {
                    "type": "string",
                    "description": "The object ID of the slide/page to get a thumbnail for",
                },
                "thumbnailSize": {
                    "type": "string",
                    "description": "The size of the thumbnail: SMALL (200px), MEDIUM (800px), or LARGE (1600px). Defaults to MEDIUM.",
                },
                "mimeType": {
                    "type": "string",
                    "description": "The MIME type of the thumbnail image: PNG or GIF. Defaults to PNG.",
                },
            },
            "required": ["presentationId", "pageObjectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        presentation_id = (parameters.get("presentationId") or "").strip()
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required")
        
        page_object_id = (parameters.get("pageObjectId") or "").strip()
        if not page_object_id:
            return ToolResult(success=False, output="", error="Page Object ID is required")
        
        thumbnail_size = (parameters.get("thumbnailSize", "MEDIUM") or "MEDIUM").strip().upper()
        if thumbnail_size not in ["SMALL", "MEDIUM", "LARGE"]:
            thumbnail_size = "MEDIUM"
        
        mime_type = (parameters.get("mimeType", "PNG") or "PNG").strip().upper()
        if mime_type not in ["PNG", "GIF"]:
            mime_type = "PNG"
        
        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}/pages/{page_object_id}/thumbnail?thumbnailProperties.thumbnailSize={thumbnail_size}"
        if mime_type != "PNG":
            url += f"&thumbnailProperties.mimeType={mime_type}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    error_msg = response.text
                    try:
                        err_data = response.json()
                        if isinstance(err_data, dict) and "error" in err_data:
                            error_msg = err_data["error"].get("message", error_msg) or "Failed to get thumbnail"
                    except:
                        pass
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
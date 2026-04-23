from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesGetPageTool(BaseTool):
    name = "google_slides_get_page"
    description = "Get detailed information about a specific slide/page in a Google Slides presentation"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Access token",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("provider_token",),
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
                    "description": "The object ID of the slide/page to retrieve",
                },
            },
            "required": ["presentationId", "pageObjectId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        presentation_id = (parameters.get("presentationId") or "").strip()
        page_object_id = (parameters.get("pageObjectId") or "").strip()
        
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required")
        if not page_object_id:
            return ToolResult(success=False, output="", error="Page Object ID is required")
        
        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}/pages/{page_object_id}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                data = response.json()
                
                if response.status_code != 200:
                    error_msg = data.get("error", {}).get("message", "Failed to get page")
                    return ToolResult(success=False, output="", error=error_msg)
                
                slide_properties = data.get("slideProperties")
                sp = None
                if slide_properties:
                    sp = {
                        "layoutObjectId": slide_properties.get("layoutObjectId"),
                        "masterObjectId": slide_properties.get("masterObjectId"),
                        "notesPage": slide_properties.get("notesPage"),
                    }
                
                output = {
                    "objectId": data.get("objectId"),
                    "pageType": data.get("pageType", "SLIDE"),
                    "pageElements": data.get("pageElements", []),
                    "slideProperties": sp,
                    "metadata": {
                        "presentationId": presentation_id,
                        "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                    },
                }
                
                return ToolResult(success=True, output=response.text, data=output)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
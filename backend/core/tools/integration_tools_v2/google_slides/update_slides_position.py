from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesUpdateSlidesPositionTool(BaseTool):
    name = "google_slides_update_slides_position"
    description = "Move one or more slides to a new position in a Google Slides presentation"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="google_drive_access_token",
                description="The access token for the Google Slides API",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("google_drive_access_token",),
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
                "slideObjectIds": {
                    "type": "string",
                    "description": "Comma-separated list of slide object IDs to move. The slides will maintain their relative order.",
                },
                "insertionIndex": {
                    "type": "number",
                    "description": "The zero-based index where the slides should be moved. All slides with indices greater than or equal to this will be shifted right.",
                },
            },
            "required": ["presentationId", "slideObjectIds", "insertionIndex"],
        }

    async def execute(self, parameters: Dict[str, Any], context: dict | None = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        presentation_id = (parameters.get("presentationId") or "").strip()
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required")
        
        slide_object_ids_str = (parameters.get("slideObjectIds") or "").strip()
        if not slide_object_ids_str:
            return ToolResult(success=False, output="", error="Slide object IDs are required")
        
        slide_object_ids = [s.strip() for s in slide_object_ids_str.split(",") if s.strip()]
        if not slide_object_ids:
            return ToolResult(success=False, output="", error="At least one slide object ID is required")
        
        try:
            insertion_index = float(parameters["insertionIndex"])
        except (KeyError, ValueError, TypeError):
            return ToolResult(success=False, output="", error="Insertion index must be a valid non-negative number")
        
        if insertion_index < 0:
            return ToolResult(success=False, output="", error="Insertion index must be a non-negative number")
        
        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"
        
        json_body = {
            "requests": [
                {
                    "updateSlidesPosition": {
                        "slideObjectIds": slide_object_ids,
                        "insertionIndex": int(insertion_index),
                    },
                },
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=json_body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
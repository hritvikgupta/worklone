from typing import Any, Dict, List
import httpx
import time
import random
import string
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesAddSlideTool(BaseTool):
    name = "google_slides_add_slide"
    description = "Add a new slide to a Google Slides presentation with a specified layout"
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
                "layout": {
                    "type": "string",
                    "description": "The predefined layout for the slide (BLANK, TITLE, TITLE_AND_BODY, TITLE_ONLY, SECTION_HEADER, etc.). Defaults to BLANK.",
                },
                "insertionIndex": {
                    "type": "number",
                    "description": "The optional zero-based index indicating where to insert the slide. If not specified, the slide is added at the end.",
                },
                "placeholderIdMappings": {
                    "type": "string",
                    "description": "JSON array of placeholder mappings to assign custom object IDs to placeholders. Format: [{\"layoutPlaceholder\":{\"type\":\"TITLE\"},\"objectId\":\"custom_title_id\"}]",
                },
            },
            "required": ["presentationId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        presentation_id = parameters.get("presentationId", "").strip()
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"
        
        PREDEFINED_LAYOUTS = [
            "BLANK",
            "CAPTION_ONLY",
            "TITLE",
            "TITLE_AND_BODY",
            "TITLE_AND_TWO_COLUMNS",
            "TITLE_ONLY",
            "SECTION_HEADER",
            "SECTION_TITLE_AND_DESCRIPTION",
            "ONE_COLUMN_TEXT",
            "MAIN_POINT",
            "BIG_NUMBER",
        ]
        
        slide_object_id = f"slide_{int(time.time() * 1000)}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=7))}"
        
        layout = parameters.get("layout", "BLANK").upper()
        if layout not in PREDEFINED_LAYOUTS:
            layout = "BLANK"
        
        create_slide_request: dict = {
            "objectId": slide_object_id,
            "slideLayoutReference": {
                "predefinedLayout": layout,
            },
        }
        
        insertion_index = parameters.get("insertionIndex")
        if insertion_index is not None and isinstance(insertion_index, (int, float)) and int(insertion_index) >= 0:
            create_slide_request["insertionIndex"] = int(insertion_index)
        
        placeholder_id_mappings = parameters.get("placeholderIdMappings")
        if isinstance(placeholder_id_mappings, str) and placeholder_id_mappings.strip():
            try:
                mappings = json.loads(placeholder_id_mappings)
                if isinstance(mappings, list) and mappings:
                    create_slide_request["placeholderIdMappings"] = mappings
            except json.JSONDecodeError:
                pass
        
        body = {
            "requests": [
                {
                    "createSlide": create_slide_request,
                }
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
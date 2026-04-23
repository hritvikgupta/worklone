from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesInsertTextTool(BaseTool):
    name = "google_slides_insert_text"
    description = "Insert text into a shape or table cell in a Google Slides presentation. Use this to add text to text boxes, shapes, or table cells."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_SLIDES_ACCESS_TOKEN",
                description="Access token for the Google Slides API",
                env_var="GOOGLE_SLIDES_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("access_token",},
            env_token_keys=("GOOGLE_SLIDES_ACCESS_TOKEN",},
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
                "objectId": {
                    "type": "string",
                    "description": "The object ID of the shape or table cell to insert text into. For table cells, use the cell object ID.",
                },
                "text": {
                    "type": "string",
                    "description": "The text to insert",
                },
                "insertionIndex": {
                    "type": "number",
                    "description": "The zero-based index at which to insert the text. If not specified, text is inserted at the beginning (index 0).",
                },
            },
            "required": ["presentationId", "objectId", "text"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        presentation_id = parameters["presentationId"].strip()
        object_id = parameters["objectId"].strip()
        text = parameters["text"]
        insertion_index = parameters.get("insertionIndex", 0)
        
        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"
        
        json_body = {
            "requests": [
                {
                    "insertText": {
                        "objectId": object_id,
                        "text": text,
                        "insertionIndex": insertion_index,
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
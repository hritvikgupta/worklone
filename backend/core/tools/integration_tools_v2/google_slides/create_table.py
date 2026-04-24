from typing import Any, Dict
import httpx
import time
import random
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesCreateTableTool(BaseTool):
    name = "google_slides_create_table"
    description = "Create a new table on a slide in a Google Slides presentation"
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
        connection = await resolve_oauth_connection("google_slides",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("GOOGLE_SLIDES_ACCESS_TOKEN",),
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
                    "description": "The object ID of the slide/page to add the table to",
                },
                "rows": {
                    "type": "number",
                    "description": "Number of rows in the table (minimum 1)",
                },
                "columns": {
                    "type": "number",
                    "description": "Number of columns in the table (minimum 1)",
                },
                "width": {
                    "type": "number",
                    "description": "Width of the table in points (default: 400)",
                },
                "height": {
                    "type": "number",
                    "description": "Height of the table in points (default: 200)",
                },
                "positionX": {
                    "type": "number",
                    "description": "X position from the left edge in points (default: 100)",
                },
                "positionY": {
                    "type": "number",
                    "description": "Y position from the top edge in points (default: 100)",
                },
            },
            "required": ["presentationId", "pageObjectId", "rows", "columns"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
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

        page_object_id = (parameters.get("pageObjectId") or "").strip()
        if not page_object_id:
            return ToolResult(success=False, output="", error="Page Object ID is required")

        rows = int(parameters["rows"])
        if rows < 1:
            return ToolResult(success=False, output="", error="Rows must be at least 1")

        columns = int(parameters["columns"])
        if columns < 1:
            return ToolResult(success=False, output="", error="Columns must be at least 1")

        random_suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=7))
        table_object_id = f"table_{int(time.time() * 1000)}_{random_suffix}"

        width_pt = float(parameters.get("width", 400))
        height_pt = float(parameters.get("height", 200))
        position_x_pt = float(parameters.get("positionX", 100))
        position_y_pt = float(parameters.get("positionY", 100))

        PT_TO_EMU = 12700
        width_emu = int(width_pt * PT_TO_EMU)
        height_emu = int(height_pt * PT_TO_EMU)
        translate_x = int(position_x_pt * PT_TO_EMU)
        translate_y = int(position_y_pt * PT_TO_EMU)

        body = {
            "requests": [
                {
                    "createTable": {
                        "objectId": table_object_id,
                        "rows": rows,
                        "columns": columns,
                        "elementProperties": {
                            "pageObjectId": page_object_id,
                            "size": {
                                "width": {
                                    "magnitude": width_emu,
                                    "unit": "EMU",
                                },
                                "height": {
                                    "magnitude": height_emu,
                                    "unit": "EMU",
                                },
                            },
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": translate_x,
                                "translateY": translate_y,
                                "unit": "EMU",
                            },
                        },
                    },
                }
            ],
        }

        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
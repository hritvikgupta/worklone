from typing import Any, Dict, List
import httpx
import base64
import time
import random
import string
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesCreateShapeTool(BaseTool):
    name = "create_shape_in_google_slides"
    description = "Create a shape (rectangle, ellipse, text box, arrow, etc.) on a slide in a Google Slides presentation"
    category = "integration"

    SHAPE_TYPES: List[str] = [
        'TEXT_BOX',
        'RECTANGLE',
        'ROUND_RECTANGLE',
        'ELLIPSE',
        'ARC',
        'BENT_ARROW',
        'BENT_UP_ARROW',
        'BEVEL',
        'BLOCK_ARC',
        'BRACE_PAIR',
        'BRACKET_PAIR',
        'CAN',
        'CHEVRON',
        'CHORD',
        'CLOUD',
        'CORNER',
        'CUBE',
        'CURVED_DOWN_ARROW',
        'CURVED_LEFT_ARROW',
        'CURVED_RIGHT_ARROW',
        'CURVED_UP_ARROW',
        'DECAGON',
        'DIAGONAL_STRIPE',
        'DIAMOND',
        'DODECAGON',
        'DONUT',
        'DOUBLE_WAVE',
        'DOWN_ARROW',
        'DOWN_ARROW_CALLOUT',
        'FOLDED_CORNER',
        'FRAME',
        'HALF_FRAME',
        'HEART',
        'HEPTAGON',
        'HEXAGON',
        'HOME_PLATE',
        'HORIZONTAL_SCROLL',
        'IRREGULAR_SEAL_1',
        'IRREGULAR_SEAL_2',
        'LEFT_ARROW',
        'LEFT_ARROW_CALLOUT',
        'LEFT_BRACE',
        'LEFT_BRACKET',
        'LEFT_RIGHT_ARROW',
        'LEFT_RIGHT_ARROW_CALLOUT',
        'LEFT_RIGHT_UP_ARROW',
        'LEFT_UP_ARROW',
        'LIGHTNING_BOLT',
        'MATH_DIVIDE',
        'MATH_EQUAL',
        'MATH_MINUS',
        'MATH_MULTIPLY',
        'MATH_NOT_EQUAL',
        'MATH_PLUS',
        'MOON',
        'NO_SMOKING',
        'NOTCHED_RIGHT_ARROW',
        'OCTAGON',
        'PARALLELOGRAM',
        'PENTAGON',
        'PIE',
        'PLAQUE',
        'PLUS',
        'QUAD_ARROW',
        'QUAD_ARROW_CALLOUT',
        'RIBBON',
        'RIBBON_2',
        'RIGHT_ARROW',
        'RIGHT_ARROW_CALLOUT',
        'RIGHT_BRACE',
        'RIGHT_BRACKET',
        'ROUND_1_RECTANGLE',
        'ROUND_2_DIAGONAL_RECTANGLE',
        'ROUND_2_SAME_RECTANGLE',
        'RIGHT_TRIANGLE',
        'SMILEY_FACE',
        'SNIP_1_RECTANGLE',
        'SNIP_2_DIAGONAL_RECTANGLE',
        'SNIP_2_SAME_RECTANGLE',
        'SNIP_ROUND_RECTANGLE',
        'STAR_10',
        'STAR_12',
        'STAR_16',
        'STAR_24',
        'STAR_32',
        'STAR_4',
        'STAR_5',
        'STAR_6',
        'STAR_7',
        'STAR_8',
        'STRIPED_RIGHT_ARROW',
        'SUN',
        'TRAPEZOID',
        'TRIANGLE',
        'UP_ARROW',
        'UP_ARROW_CALLOUT',
        'UP_DOWN_ARROW',
        'UTURN_ARROW',
        'VERTICAL_SCROLL',
        'WAVE',
        'WEDGE_ELLIPSE_CALLOUT',
        'WEDGE_RECTANGLE_CALLOUT',
        'WEDGE_ROUND_RECTANGLE_CALLOUT',
        'FLOW_CHART_ALTERNATE_PROCESS',
        'FLOW_CHART_COLLATE',
        'FLOW_CHART_CONNECTOR',
        'FLOW_CHART_DECISION',
        'FLOW_CHART_DELAY',
        'FLOW_CHART_DISPLAY',
        'FLOW_CHART_DOCUMENT',
        'FLOW_CHART_EXTRACT',
        'FLOW_CHART_INPUT_OUTPUT',
        'FLOW_CHART_INTERNAL_STORAGE',
        'FLOW_CHART_MAGNETIC_DISK',
        'FLOW_CHART_MAGNETIC_DRUM',
        'FLOW_CHART_MAGNETIC_TAPE',
        'FLOW_CHART_MANUAL_INPUT',
        'FLOW_CHART_MANUAL_OPERATION',
        'FLOW_CHART_MERGE',
        'FLOW_CHART_MULTIDOCUMENT',
        'FLOW_CHART_OFFLINE_STORAGE',
        'FLOW_CHART_OFFPAGE_CONNECTOR',
        'FLOW_CHART_ONLINE_STORAGE',
        'FLOW_CHART_OR',
        'FLOW_CHART_PREDEFINED_PROCESS',
        'FLOW_CHART_PREPARATION',
        'FLOW_CHART_PROCESS',
        'FLOW_CHART_PUNCHED_CARD',
        'FLOW_CHART_PUNCHED_TAPE',
        'FLOW_CHART_SORT',
        'FLOW_CHART_SUMMING_JUNCTION',
        'FLOW_CHART_TERMINATOR',
        'ARROW_EAST',
        'ARROW_NORTH_EAST',
        'ARROW_NORTH',
        'SPEECH',
        'STARBURST',
        'TEARDROP',
        'ELLIPSE_RIBBON',
        'ELLIPSE_RIBBON_2',
        'CLOUD_CALLOUT',
        'CUSTOM',
    ]

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> List[CredentialRequirement]:
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
                    "description": "The object ID of the slide/page to add the shape to",
                },
                "shapeType": {
                    "type": "string",
                    "description": "The type of shape to create. Common types: TEXT_BOX, RECTANGLE, ROUND_RECTANGLE, ELLIPSE, TRIANGLE, DIAMOND, STAR_5, ARROW_EAST, HEART, CLOUD",
                },
                "width": {
                    "type": "number",
                    "description": "Width of the shape in points (default: 200)",
                },
                "height": {
                    "type": "number",
                    "description": "Height of the shape in points (default: 100)",
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
            "required": ["presentationId", "pageObjectId", "shapeType"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        presentation_id = parameters.get("presentationId", "").strip()
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required")

        page_object_id = parameters.get("pageObjectId", "").strip()
        if not page_object_id:
            return ToolResult(success=False, output="", error="Page Object ID is required")

        shape_type_input = parameters.get("shapeType", "RECTANGLE").strip().upper()
        shape_type = shape_type_input if shape_type_input in self.SHAPE_TYPES else "RECTANGLE"

        width = parameters.get("width", 200)
        height = parameters.get("height", 100)
        position_x = parameters.get("positionX", 100)
        position_y = parameters.get("positionY", 100)

        PT_TO_EMU = 12700
        width_emu = int(width * PT_TO_EMU)
        height_emu = int(height * PT_TO_EMU)
        translate_x = int(position_x * PT_TO_EMU)
        translate_y = int(position_y * PT_TO_EMU)

        shape_object_id = f"shape_{int(time.time() * 1000)}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=7))}"

        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"

        body = {
            "requests": [
                {
                    "createShape": {
                        "objectId": shape_object_id,
                        "shapeType": shape_type,
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
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                    except Exception:
                        data = {}
                    create_shape_reply = data.get("replies", [{}])[0].get("createShape", {})
                    shape_id = create_shape_reply.get("objectId", "")
                    output_data = {
                        "shapeId": shape_id,
                        "shapeType": shape_type,
                        "metadata": {
                            "presentationId": presentation_id,
                            "pageObjectId": page_object_id,
                            "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                        },
                    }
                    return ToolResult(success=True, output=json.dumps(output_data), data=output_data)
                else:
                    return ToolResult(success=False, output="", error=response.text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
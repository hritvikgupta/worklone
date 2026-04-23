from typing import Any, Dict
import httpx
import time
import random
import string
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesAddImageTool(BaseTool):
    name = "google_slides_add_image"
    description = "Insert an image into a specific slide in a Google Slides presentation"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
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
                    "description": "The object ID of the slide/page to add the image to",
                },
                "imageUrl": {
                    "type": "string",
                    "description": "The publicly accessible URL of the image (must be PNG, JPEG, or GIF, max 50MB)",
                },
                "width": {
                    "type": "number",
                    "description": "Width of the image in points (default: 300)",
                },
                "height": {
                    "type": "number",
                    "description": "Height of the image in points (default: 200)",
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
            "required": ["presentationId", "pageObjectId", "imageUrl"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        presentation_id = (parameters.get("presentationId") or "").strip()
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required")

        page_object_id = (parameters.get("pageObjectId") or "").strip()
        image_url = (parameters.get("imageUrl") or "").strip()
        if not page_object_id or not image_url:
            return ToolResult(success=False, output="", error="Page Object ID and Image URL are required")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"

        image_object_id = f"image_{int(time.time() * 1000)}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=7))}"

        PT_TO_EMU = 12700
        width_pt = parameters.get("width", 300)
        height_pt = parameters.get("height", 200)
        position_x_pt = parameters.get("positionX", 100)
        position_y_pt = parameters.get("positionY", 100)

        width_emu = int(width_pt * PT_TO_EMU)
        height_emu = int(height_pt * PT_TO_EMU)
        translate_x = int(position_x_pt * PT_TO_EMU)
        translate_y = int(position_y_pt * PT_TO_EMU)

        body = {
            "requests": [
                {
                    "createImage": {
                        "objectId": image_object_id,
                        "url": image_url,
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

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201]:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

                data = response.json()
                replies = data.get("replies", [])
                create_image_reply = replies[0].get("createImage", {}) if replies else {}
                image_id = create_image_reply.get("objectId", "")

                metadata = {
                    "presentationId": presentation_id,
                    "pageObjectId": page_object_id,
                    "imageUrl": image_url,
                    "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                }
                output_data = {
                    "imageId": image_id,
                    "metadata": metadata,
                }
                output_str = json.dumps(output_data)
                return ToolResult(success=True, output=output_str, data=output_data)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
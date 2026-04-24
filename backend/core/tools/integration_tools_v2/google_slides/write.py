from typing import Any, Dict, List
import httpx
import time
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesWriteTool(BaseTool):
    name = "google_slides_write"
    description = "Write or update content in a Google Slides presentation"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PROVIDER_ACCESS_TOKEN",
                description="Access token",
                env_var="PROVIDER_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection("google_slides",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("PROVIDER_ACCESS_TOKEN",),
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
                "content": {
                    "type": "string",
                    "description": "The content to write to the slide",
                },
                "slideIndex": {
                    "type": "number",
                    "description": "The index of the slide to write to (defaults to first slide)",
                },
            },
            "required": ["presentationId", "content"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        presentation_id = parameters.get("presentationId", "").strip()
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required")

        content = parameters.get("content", "")
        if not content:
            return ToolResult(success=False, output="", error="Content is required")

        slide_index_raw = parameters.get("slideIndex")
        if slide_index_raw is None:
            slide_index = 0
        elif isinstance(slide_index_raw, str):
            try:
                slide_index = int(slide_index_raw)
            except ValueError:
                return ToolResult(
                    success=False,
                    output="",
                    error="Slide index must be a non-negative number",
                )
        else:
            slide_index = int(slide_index_raw)

        if slide_index < 0:
            return ToolResult(
                success=False,
                output="",
                error="Slide index must be a non-negative number",
            )

        headers_auth = {"Authorization": f"Bearer {access_token}"}
        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=headers_auth)
                if resp.status_code not in [200]:
                    return ToolResult(
                        success=False,
                        output="",
                        error=resp.text or f"HTTP {resp.status_code}",
                    )

                presentation_data = resp.json()
                slides = presentation_data.get("slides", [])
                if slide_index >= len(slides):
                    metadata = {
                        "presentationId": presentation_id,
                        "title": presentation_data.get("title", "Updated Presentation"),
                        "mimeType": "application/vnd.google-apps.presentation",
                        "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                    }
                    output_dict = {"updatedContent": False, "metadata": metadata}
                    return ToolResult(
                        success=False,
                        output=json.dumps(output_dict),
                        error=f"Slide at index {slide_index} not found",
                        data=output_dict,
                    )

                slide = slides[slide_index]
                metadata = {
                    "presentationId": presentation_id,
                    "title": presentation_data.get("title", "Updated Presentation"),
                    "mimeType": "application/vnd.google-apps.presentation",
                    "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                }

                text_box_id = f"textbox_{int(time.time() * 1000)}"
                requests = [
                    {
                        "createShape": {
                            "objectId": text_box_id,
                            "shapeType": "TEXT_BOX",
                            "elementProperties": {
                                "pageObjectId": slide["objectId"],
                                "size": {
                                    "width": {"magnitude": 400, "unit": "PT"},
                                    "height": {"magnitude": 100, "unit": "PT"},
                                },
                                "transform": {
                                    "scaleX": 1,
                                    "scaleY": 1,
                                    "translateX": 50,
                                    "translateY": 100,
                                    "unit": "PT",
                                },
                            },
                        }
                    },
                    {
                        "insertText": {
                            "objectId": text_box_id,
                            "text": content,
                            "insertionIndex": 0,
                        }
                    },
                ]

                batch_url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"
                headers_post = {
                    **headers_auth,
                    "Content-Type": "application/json",
                }
                resp_update = await client.post(
                    batch_url, headers=headers_post, json={"requests": requests}
                )

                if resp_update.status_code not in [200]:
                    output_dict = {"updatedContent": False, "metadata": metadata}
                    return ToolResult(
                        success=False,
                        output=json.dumps(output_dict),
                        error="Failed to update presentation",
                        data=output_dict,
                    )

                output_dict = {"updatedContent": True, "metadata": metadata}
                update_data = resp_update.json() if resp_update.text else {}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_dict),
                    data={"output": output_dict, **update_data},
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
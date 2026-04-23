from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesCreateTool(BaseTool):
    name = "google_slides_create"
    description = "Create a new Google Slides presentation"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_DRIVE_ACCESS_TOKEN",
                description="Access token for Google Drive and Slides APIs",
                env_var="GOOGLE_DRIVE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-drive",
            context=context,
            context_token_keys=("access_token",),
            env_token_keys=("GOOGLE_DRIVE_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the presentation to create",
                },
                "content": {
                    "type": "string",
                    "description": "The content to add to the first slide",
                },
                "folderSelector": {
                    "type": "string",
                    "description": "Google Drive folder ID to create the presentation in (e.g., 1ABCxyz...)",
                },
            },
            "required": ["title"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)

        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")

        title = parameters.get("title")
        if not title:
            return ToolResult(success=False, output="", error="Title is required.")

        content = parameters.get("content", "").strip()
        folder_selector = parameters.get("folderSelector", "").strip()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        url = "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true"

        body: Dict[str, Any] = {
            "name": title,
            "mimeType": "application/vnd.google-apps.presentation",
        }
        if folder_selector:
            body["parents"] = [folder_selector]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code not in [200, 201]:
                    return ToolResult(
                        success=False, output=response.text, error=f"API error: {response.status_code} - {response.text}"
                    )

                try:
                    data = response.json()
                except json.JSONDecodeError:
                    return ToolResult(
                        success=False,
                        output=response.text,
                        error="Invalid JSON response from API",
                    )

                presentation_id = data.get("id")
                if not presentation_id:
                    return ToolResult(
                        success=False,
                        output=response.text,
                        error="No presentation ID in response",
                    )

                title_resp = data.get("name", title)
                metadata = {
                    "presentationId": presentation_id,
                    "title": title_resp or "Untitled Presentation",
                    "mimeType": "application/vnd.google-apps.presentation",
                    "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                }

                # Optionally add content to first slide, matching postProcess behavior
                if content:
                    try:
                        pages_url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}/pages"
                        pages_response = await client.get(pages_url, headers=headers)
                        if pages_response.status_code == 200:
                            try:
                                pages_data = pages_response.json()
                                slides = pages_data.get("slides", [])
                                if slides:
                                    first_slide_id = slides[0]["objectId"]
                                    batch_requests = [
                                        {
                                            "createShape": {
                                                "objectId": "myContentTextBox",
                                                "shapeType": "TEXT_BOX",
                                                "elementProperties": {
                                                    "pageObjectId": first_slide_id,
                                                    "size": {
                                                        "height": {"magnitude": 72.0, "unit": "PT"},
                                                        "width": {"magnitude": 360.0, "unit": "PT"},
                                                    },
                                                    "transform": {
                                                        "scaleX": 1.0,
                                                        "scaleY": 1.0,
                                                        "translateX": 72.0,
                                                        "translateY": 144.0,
                                                        "unit": "PT",
                                                    },
                                                },
                                            }
                                        },
                                        {
                                            "insertText": {
                                                "objectId": "myContentTextBox",
                                                "insertionIndex": 0,
                                                "text": content,
                                            }
                                        },
                                    ]
                                    batch_url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"
                                    write_response = await client.post(
                                        batch_url, headers=headers, json={"requests": batch_requests}
                                    )
                                    if write_response.status_code not in [200, 201]:
                                        print(f"Warning: Failed to add content - {write_response.status_code}: {write_response.text}")
                            except json.JSONDecodeError:
                                print("Warning: Invalid JSON when fetching pages")
                        else:
                            print(f"Warning: Failed to fetch pages - {pages_response.status_code}")
                    except Exception as content_error:
                        print(f"Warning: Error adding content to presentation: {str(content_error)}")

                output_data = {"metadata": metadata}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )

        except httpx.RequestError as e:
            return ToolResult(success=False, output="", error=f"Network error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
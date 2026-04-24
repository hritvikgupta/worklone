from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesDuplicateObjectTool(BaseTool):
    name = "google_slides_duplicate_object"
    description = "Duplicate an object (slide, shape, image, table, etc.) in a Google Slides presentation"
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
        connection = await resolve_oauth_connection("google_slides",
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
                "objectId": {
                    "type": "string",
                    "description": "The object ID of the element or slide to duplicate",
                },
                "objectIds": {
                    "type": "string",
                    "description": "Optional JSON object mapping source object IDs (within the slide being duplicated) to new object IDs for the duplicates. Format: {\"sourceId1\":\"newId1\",\"sourceId2\":\"newId2\"}",
                },
            },
            "required": ["presentationId", "objectId"],
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
        object_id = (parameters.get("objectId") or "").strip()
        if not presentation_id or not object_id:
            return ToolResult(success=False, output="", error="Presentation ID and object ID are required.")

        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"

        duplicate_request: Dict[str, Any] = {
            "objectId": object_id,
        }

        object_ids_str = (parameters.get("objectIds") or "").strip()
        if object_ids_str:
            try:
                mapping = json.loads(object_ids_str)
                if isinstance(mapping, dict) and not isinstance(mapping, list):
                    duplicate_request["objectIds"] = mapping
            except json.JSONDecodeError:
                pass

        body = {
            "requests": [
                {
                    "duplicateObject": duplicate_request,
                },
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)

                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        duplicate_reply = data.get("replies", [{}])[0].get("duplicateObject", {})
                        duplicated_object_id = duplicate_reply.get("objectId", "")
                        output_data = {
                            "duplicatedObjectId": duplicated_object_id,
                            "metadata": {
                                "presentationId": presentation_id,
                                "sourceObjectId": object_id,
                                "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                            },
                        }
                        return ToolResult(
                            success=True,
                            output=json.dumps(output_data),
                            data=output_data,
                        )
                    except json.JSONDecodeError:
                        return ToolResult(success=False, output=response.text, error="Invalid JSON response from API")
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", str(error_data))
                    except json.JSONDecodeError:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
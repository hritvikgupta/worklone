from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesReadTool(BaseTool):
    name = "google_slides_read"
    description = "Read content from a Google Slides presentation"
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
            },
            "required": ["presentationId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        presentation_id = (parameters.get("presentationId") or "").strip()
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    slides = data.get("slides", [])
                    presentation_id_from_api = data.get("presentationId")
                    metadata = {
                        "presentationId": presentation_id_from_api,
                        "title": data.get("title", "Untitled Presentation"),
                        "pageSize": data.get("pageSize"),
                        "mimeType": "application/vnd.google-apps.presentation",
                        "url": f"https://docs.google.com/presentation/d/{presentation_id_from_api}/edit" if presentation_id_from_api else "",
                    }
                    result = {
                        "slides": slides,
                        "metadata": metadata,
                    }
                    return ToolResult(success=True, output=json.dumps(result), data=result)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleSlidesReplaceAllTextTool(BaseTool):
    name = "google_slides_replace_all_text"
    description = "Find and replace all occurrences of text throughout a Google Slides presentation"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_ACCESS_TOKEN",
                description="Access token for the Google Slides API",
                env_var="GOOGLE_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection("google_slides",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_ACCESS_TOKEN",),
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
                "findText": {
                    "type": "string",
                    "description": "The text to find (e.g., {{placeholder}})",
                },
                "replaceText": {
                    "type": "string",
                    "description": "The text to replace with",
                },
                "matchCase": {
                    "type": "boolean",
                    "description": "Whether the search should be case-sensitive (default: true)",
                },
                "pageObjectIds": {
                    "type": "string",
                    "description": "Comma-separated list of slide object IDs to limit replacements to specific slides (leave empty for all slides)",
                },
            },
            "required": ["presentationId", "findText", "replaceText"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        presentation_id = (parameters.get("presentationId") or "").strip()
        if not presentation_id:
            return ToolResult(success=False, output="", error="Presentation ID is required")
        
        find_text = parameters.get("findText", "")
        if not find_text:
            return ToolResult(success=False, output="", error="Find text is required")
        
        replace_text = parameters.get("replaceText")
        if replace_text is None:
            return ToolResult(success=False, output="", error="Replace text is required")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://slides.googleapis.com/v1/presentations/{presentation_id}:batchUpdate"
        
        replace_all_text = {
            "containsText": {
                "text": find_text,
                "matchCase": parameters.get("matchCase") is not False,
            },
            "replaceText": replace_text,
        }
        
        page_object_ids_str = (parameters.get("pageObjectIds") or "").strip()
        if page_object_ids_str:
            page_ids = [pid.strip() for pid in page_object_ids_str.split(",") if pid.strip()]
            if page_ids:
                replace_all_text["pageObjectIds"] = page_ids
        
        body = {
            "requests": [
                {
                    "replaceAllText": replace_all_text,
                },
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    try:
                        data = response.json()
                        replies = data.get("replies", [])
                        replace_result = replies[0].get("replaceAllText", {}) if replies else {}
                        occurrences_changed = replace_result.get("occurrencesChanged", 0)
                        
                        output_data = {
                            "occurrencesChanged": occurrences_changed,
                            "metadata": {
                                "presentationId": presentation_id,
                                "findText": find_text,
                                "replaceText": replace_text,
                                "url": f"https://docs.google.com/presentation/d/{presentation_id}/edit",
                            },
                        }
                        return ToolResult(
                            success=True,
                            output=json.dumps(output_data),
                            data=output_data,
                        )
                    except Exception:
                        return ToolResult(success=False, output=response.text, error="Failed to parse response")
                else:
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("error", {}).get("message", "Failed to replace text")
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import base64
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleFormsDeleteWatchTool(BaseTool):
    name = "google_forms_delete_watch"
    description = "Delete a notification watch from a form"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_FORMS_ACCESS_TOKEN",
                description="OAuth access token",
                env_var="GOOGLE_FORMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GOOGLE_FORMS_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "formId": {
                    "type": "string",
                    "description": "Google Forms form ID",
                },
                "watchId": {
                    "type": "string",
                    "description": "Watch ID to delete",
                },
            },
            "required": ["formId", "watchId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        form_id = parameters["formId"]
        watch_id = parameters["watchId"]
        url = f"https://forms.googleapis.com/v1/forms/{form_id}/watches/{watch_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                try:
                    data = response.json()
                except:
                    data = {}
                
                if response.status_code in [200, 204]:
                    output_data = {"deleted": True}
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    error_data = data.get("error", {}) if isinstance(data, dict) else {}
                    error_msg = error_data.get("message") if isinstance(error_data, dict) else response.text
                    if not error_msg:
                        error_msg = "Failed to delete watch"
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
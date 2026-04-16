from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleFormsSetPublishSettingsTool(BaseTool):
    name = "google_forms_set_publish_settings"
    description = "Update the publish settings of a form (publish/unpublish, accept responses)"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GOOGLE_FORMS_ACCESS_TOKEN",
                description="Access token",
                env_var="GOOGLE_FORMS_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google-forms",
            context=context,
            context_token_keys=("provider_token",),
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
                "isPublished": {
                    "type": "boolean",
                    "description": "Whether the form is published and visible to others",
                },
                "isAcceptingResponses": {
                    "type": "boolean",
                    "description": "Whether the form accepts responses (forced to false if isPublished is false)",
                },
            },
            "required": ["formId", "isPublished"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = f"https://forms.googleapis.com/v1/forms/{parameters['formId']}:batchUpdate"
        
        publish_state = {
            "isPublished": parameters["isPublished"],
        }
        is_accepting_responses = parameters.get("isAcceptingResponses")
        if is_accepting_responses is not None:
            publish_state["isAcceptingResponses"] = is_accepting_responses
        
        body = {
            "publishSettings": {
                "publishState": publish_state,
            },
            "updateMask": "publishState",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GoogleFormsCreateWatchTool(BaseTool):
    name = "google_forms_create_watch"
    description = "Create a notification watch for form changes (schema changes or new responses)"
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
                    "description": "Google Forms form ID to watch",
                },
                "eventType": {
                    "type": "string",
                    "description": "Event type to watch: SCHEMA (form changes) or RESPONSES (new submissions)",
                },
                "topicName": {
                    "type": "string",
                    "description": "The Cloud Pub/Sub topic name (format: projects/{project}/topics/{topic})",
                },
                "watchId": {
                    "type": "string",
                    "description": "Custom watch ID (4-63 chars, lowercase letters, numbers, hyphens)",
                },
            },
            "required": ["formId", "eventType", "topicName"],
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
        url = f"https://forms.googleapis.com/v1/forms/{form_id}:createWatch"
        
        body = {
            "watch": {
                "target": {
                    "topic": {
                        "topicName": parameters["topicName"],
                    },
                },
                "eventType": parameters["eventType"],
            },
        }
        if "watchId" in parameters and parameters["watchId"]:
            body["watchId"] = parameters["watchId"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
from typing import Any, Dict
import httpx
import json
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class LoopsSendTransactionalEmailTool(BaseTool):
    name = "loops_send_transactional_email"
    description = "Send a transactional email to a recipient using a Loops template. Supports dynamic data variables for personalization and optionally adds the recipient to your audience."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="apiKey",
                description="Loops API key for authentication",
                env_var="LOOPS_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "loops",
            context=context,
            context_token_keys=("apiKey",),
            env_token_keys=("LOOPS_API_KEY",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=False,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "The email address of the recipient",
                },
                "transactionalId": {
                    "type": "string",
                    "description": "The ID of the transactional email template to send",
                },
                "dataVariables": {
                    "type": "object",
                    "description": "Template data variables as key-value pairs (string or number values)",
                    "additionalProperties": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "number"},
                        ]
                    },
                },
                "addToAudience": {
                    "type": "boolean",
                    "description": "Whether to create the recipient as a contact if they do not already exist (default: false)",
                },
                "attachments": {
                    "type": "array",
                    "description": "Array of file attachments. Each object must have filename (string), contentType (MIME type string), and data (base64-encoded string).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "contentType": {"type": "string"},
                            "data": {"type": "string"},
                        },
                        "required": ["filename", "contentType", "data"],
                    },
                },
            },
            "required": ["email", "transactionalId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://app.loops.so/api/v1/transactional"
        
        body: dict[str, Any] = {
            "email": parameters["email"].strip(),
            "transactionalId": parameters["transactionalId"].strip(),
        }
        
        if "dataVariables" in parameters:
            data_variables = parameters["dataVariables"]
            body["dataVariables"] = json.loads(data_variables) if isinstance(data_variables, str) else data_variables
        
        if "addToAudience" in parameters:
            body["addToAudience"] = parameters["addToAudience"]
        
        if "attachments" in parameters:
            attachments = parameters["attachments"]
            body["attachments"] = json.loads(attachments) if isinstance(attachments, str) else attachments
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    return ToolResult(success=False, output="", error="Invalid JSON from API")
                
                if data.get("success"):
                    return ToolResult(success=True, output='{"success": true}', data=data)
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=data.get("message") or "Failed to send transactional email",
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
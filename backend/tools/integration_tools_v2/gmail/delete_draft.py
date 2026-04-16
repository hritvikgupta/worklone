from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GmailDeleteDraftTool(BaseTool):
    name = "Gmail Delete Draft"
    description = "Delete a specific draft from Gmail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GMAIL_ACCESS_TOKEN",
                description="Access token for Gmail API",
                env_var="GMAIL_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "google",
            context=context,
            context_token_keys=("accessToken",),
            env_token_keys=("GMAIL_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "draftId": {
                    "type": "string",
                    "description": "ID of the draft to delete",
                },
            },
            "required": ["draftId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        draft_id = parameters["draftId"]
        url = f"https://gmail.googleapis.com/gmail/v1/drafts/{draft_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    output_data = {"deleted": True, "draftId": draft_id}
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    try:
                        error_json = response.json()
                        error_msg = (
                            error_json.get("error", {}).get("message", str(error_json))
                            if error_json
                            else response.text
                        )
                    except Exception:
                        error_msg = response.text
                    output_data = {"deleted": False, "draftId": draft_id}
                    return ToolResult(
                        success=False,
                        output=json.dumps(output_data),
                        error=error_msg,
                    )
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
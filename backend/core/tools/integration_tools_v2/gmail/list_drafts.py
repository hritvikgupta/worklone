from typing import Any, Dict
import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GmailListDraftsTool(BaseTool):
    name = "gmail_list_drafts"
    description = "List all drafts in a Gmail account"
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
            context_token_keys=("gmail_token",),
            env_token_keys=("GMAIL_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of drafts to return (default: 100, max: 500)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token for paginated results",
                },
                "query": {
                    "type": "string",
                    "description": "Search query to filter drafts (same syntax as Gmail search)",
                },
            },
            "required": [],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        url = "https://gmail.googleapis.com/gmail/v1/users/me/drafts"
        params = {
            "maxResults": parameters.get("maxResults"),
            "pageToken": parameters.get("pageToken"),
            "q": parameters.get("query"),
        }
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    drafts = []
                    for draft in data.get("drafts", []):
                        message = draft.get("message", {})
                        drafts.append({
                            "id": draft.get("id"),
                            "messageId": message.get("id"),
                            "threadId": message.get("threadId"),
                        })
                    output_data = {
                        "drafts": drafts,
                        "resultSizeEstimate": data.get("resultSizeEstimate", 0),
                        "nextPageToken": data.get("nextPageToken"),
                    }
                    return ToolResult(success=True, output=str(output_data), data=output_data)
                else:
                    try:
                        err_data = response.json()
                        error_msg = err_data.get("error", {}).get("message", response.text)
                    except Exception:
                        error_msg = response.text
                    return ToolResult(success=False, output="", error=error_msg)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
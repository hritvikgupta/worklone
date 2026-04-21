from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class GmailListThreadsTool(BaseTool):
    name = "gmail_list_threads"
    description = "List email threads in a Gmail account"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="GMAIL_ACCESS_TOKEN",
                description="Access token",
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
                    "description": "Maximum number of threads to return (default: 100, max: 500)",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Page token for paginated results",
                },
                "query": {
                    "type": "string",
                    "description": "Search query to filter threads (same syntax as Gmail search)",
                },
                "labelIds": {
                    "type": "string",
                    "description": "Comma-separated label IDs to filter threads by",
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
        
        url = "https://gmail.googleapis.com/gmail/v1/users/me/threads"
        params: dict[str, Any] = {}
        if "maxResults" in parameters:
            params["maxResults"] = parameters["maxResults"]
        if "pageToken" in parameters:
            params["pageToken"] = parameters["pageToken"]
        if "query" in parameters and parameters["query"]:
            params["q"] = parameters["query"]
        if "labelIds" in parameters and parameters["labelIds"]:
            labels = [l.strip() for l in str(parameters["labelIds"]).split(",") if l.strip()]
            if labels:
                params["labelIds"] = labels
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
import httpx
import os
from urllib.parse import urlencode
from typing import Any, Dict
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailListInboxesTool(BaseTool):
    name = "agentmail_list_inboxes"
    description = "List all email inboxes in AgentMail"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="AGENTMAIL_API_KEY",
                description="AgentMail API key",
                env_var="AGENTMAIL_API_KEY",
                required=True,
                auth_type="api_key",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        access_token = context.get("AGENTMAIL_API_KEY") if context else None
        if access_token is None or self._is_placeholder_token(access_token):
            access_token = os.getenv("AGENTMAIL_API_KEY")
        return access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "Maximum number of inboxes to return",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Pagination token for next page of results",
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
        }
        
        query_params: Dict[str, Any] = {}
        limit = parameters.get("limit")
        if limit is not None:
            query_params["limit"] = limit
        page_token = parameters.get("pageToken")
        if page_token:
            query_params["page_token"] = page_token
        qs = urlencode(query_params)
        url = "https://api.agentmail.to/v0/inboxes"
        if qs:
            url += f"?{qs}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
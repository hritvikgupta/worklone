from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentMailListDraftsTool(BaseTool):
    name = "agentmail_list_drafts"
    description = "List email drafts in an inbox in AgentMail"
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
        access_token = None
        if context is not None:
            access_token = context.get("AGENTMAIL_API_KEY")
        if access_token is None:
            access_token = os.getenv("AGENTMAIL_API_KEY")
        return access_token or ""

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to list drafts from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of drafts to return",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Pagination token for next page of results",
                },
            },
            "required": ["inboxId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        
        inbox_id = parameters.get("inboxId", "").strip()
        if not inbox_id:
            return ToolResult(success=False, output="", error="Invalid or missing inboxId")
        
        query_params = {}
        limit = parameters.get("limit")
        if limit:
            query_params["limit"] = limit
        page_token = parameters.get("pageToken")
        if page_token:
            query_params["page_token"] = page_token
        
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/drafts"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
import os
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailListThreadsTool(BaseTool):
    name = "agentmail_list_threads"
    description = "List email threads in AgentMail"
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

    async def _resolve_api_key(self, context: dict | None) -> str:
        api_key = (context or {}).get("AGENTMAIL_API_KEY") or ""
        if self._is_placeholder_token(api_key):
            api_key = os.getenv("AGENTMAIL_API_KEY") or ""
        return api_key

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to list threads from"
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of threads to return"
                },
                "pageToken": {
                    "type": "string",
                    "description": "Pagination token for next page of results"
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated labels to filter threads by"
                },
                "before": {
                    "type": "string",
                    "description": "Filter threads before this ISO 8601 timestamp"
                },
                "after": {
                    "type": "string",
                    "description": "Filter threads after this ISO 8601 timestamp"
                }
            },
            "required": ["inboxId"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = await self._resolve_api_key(context)
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        inbox_id = parameters.get("inboxId", "").strip()
        if not inbox_id:
            return ToolResult(success=False, output="", error="Inbox ID is required.")
        
        params: Dict[str, Any] = {}
        limit = parameters.get("limit")
        if limit is not None:
            params["limit"] = limit
        page_token = parameters.get("pageToken")
        if page_token:
            params["page_token"] = page_token
        labels = parameters.get("labels")
        if labels:
            label_list = [l.strip() for l in str(labels).split(",") if l.strip()]
            params["labels"] = label_list
        before = parameters.get("before")
        if before:
            params["before"] = before
        after = parameters.get("after")
        if after:
            params["after"] = after
        
        url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/threads"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
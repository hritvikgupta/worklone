import httpx
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class AgentmailListMessagesTool(BaseTool):
    name = "agentmail_list_messages"
    description = "List messages in an inbox in AgentMail"
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

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "inboxId": {
                    "type": "string",
                    "description": "ID of the inbox to list messages from",
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of messages to return",
                },
                "pageToken": {
                    "type": "string",
                    "description": "Pagination token for next page of results",
                },
            },
            "required": ["inboxId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        api_key = context.get("AGENTMAIL_API_KEY") if context else None
        
        if self._is_placeholder_token(api_key):
            return ToolResult(success=False, output="", error="API key not configured.")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        inbox_id = parameters["inboxId"].strip()
        base_url = f"https://api.agentmail.to/v0/inboxes/{inbox_id}/messages"
        query_params = {}
        if parameters.get("limit") is not None:
            query_params["limit"] = parameters["limit"]
        if parameters.get("pageToken") is not None:
            query_params["page_token"] = parameters["pageToken"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(base_url, headers=headers, params=query_params)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
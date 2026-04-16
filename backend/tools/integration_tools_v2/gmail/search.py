from typing import Any, Dict
import httpx
import json
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class GmailSearchTool(BaseTool):
    name = "gmail_search"
    description = "Search emails in Gmail. Returns API-aligned fields only."
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def _extract_header(self, message: Dict[str, Any], header_name: str) -> str:
        headers = message.get("payload", {}).get("headers", [])
        header_name_lower = header_name.lower()
        for header in headers:
            if header.get("name", "").lower() == header_name_lower:
                return header["value"]
        return ""

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
                "query": {
                    "type": "string",
                    "description": "Search query for emails",
                },
                "maxResults": {
                    "type": "number",
                    "description": "Maximum number of results to return (e.g., 10, 25, 50)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        search_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        search_params: Dict[str, Any] = {
            "q": parameters["query"],
        }
        if "maxResults" in parameters and parameters["maxResults"] is not None:
            search_params["maxResults"] = int(parameters["maxResults"])
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                search_response = await client.get(search_url, headers=headers, params=search_params)
                
                if search_response.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Gmail search API error: HTTP {search_response.status_code} - {search_response.text}",
                    )
                    
                search_data = search_response.json()
                messages = search_data.get("messages", [])
                
                if not messages:
                    output_data = {"results": []}
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                
                results = []
                for msg in messages:
                    msg_id = msg["id"]
                    thread_id = msg.get("threadId", "")
                    detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=full"
                    
                    try:
                        detail_response = await client.get(detail_url, headers=headers)
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            snippet = detail_data.get("snippet", msg.get("snippet", ""))
                            subject = self._extract_header(detail_data, "Subject")
                            from_addr = self._extract_header(detail_data, "From")
                            date_str = self._extract_header(detail_data, "Date")
                            processed = {
                                "id": msg_id,
                                "threadId": detail_data.get("threadId", thread_id),
                                "subject": subject,
                                "from": from_addr,
                                "date": date_str,
                                "snippet": snippet,
                            }
                        else:
                            processed = {"id": msg_id, "threadId": thread_id}
                        results.append(processed)
                    except Exception:
                        results.append({"id": msg_id, "threadId": thread_id})
                
                output_data = {"results": results}
                return ToolResult(
                    success=True,
                    output=json.dumps(output_data),
                    data=output_data,
                )
                
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
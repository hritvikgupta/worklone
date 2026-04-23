from typing import Any, Dict
import httpx
import os
import json
from urllib.parse import urlencode
from backend.core.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement

class LoopsListTransactionalEmailsTool(BaseTool):
    name = "loops_list_transactional_emails"
    description = "Retrieve a list of published transactional email templates from your Loops account. Returns each template with its ID, name, last updated timestamp, and data variables."
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
        token = context.get("apiKey") if context else None
        if self._is_placeholder_token(token or ""):
            token = os.getenv("LOOPS_API_KEY")
        return token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "perPage": {
                    "type": "string",
                    "description": "Number of results per page (10-50, default: 20)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response to fetch the next page",
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
        
        per_page = parameters.get("perPage")
        cursor_param = parameters.get("cursor")
        
        base_url = "https://app.loops.so/api/v1/transactional"
        query_params: Dict[str, str] = {}
        if per_page:
            query_params["perPage"] = per_page
        if cursor_param:
            query_params["cursor"] = cursor_param
        
        url = base_url
        if query_params:
            url += "?" + urlencode(query_params)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    
                    data_data = data.get("data")
                    if data_data is None and not isinstance(data, list):
                        error_msg = data.get("message", "Failed to list transactional emails")
                        output_data = {
                            "transactionalEmails": [],
                            "pagination": {
                                "totalResults": 0,
                                "returnedResults": 0,
                                "perPage": 0,
                                "totalPages": 0,
                                "nextCursor": None,
                                "nextPage": None,
                            },
                        }
                        return ToolResult(
                            success=False,
                            output=json.dumps(output_data),
                            data=output_data,
                            error=error_msg,
                        )
                    
                    emails = data_data if data_data is not None else (data if isinstance(data, list) else [])
                    
                    transformed_emails = [
                        {
                            "id": str(email.get("id", "")),
                            "name": str(email.get("name", "")),
                            "lastUpdated": str(email.get("lastUpdated", "")),
                            "dataVariables": email.get("dataVariables", []),
                        }
                        for email in emails
                    ]
                    
                    pag = data.get("pagination", {})
                    pagination = {
                        "totalResults": pag.get("totalResults", len(emails)),
                        "returnedResults": pag.get("returnedResults", len(emails)),
                        "perPage": pag.get("perPage", 20),
                        "totalPages": pag.get("totalPages", 1),
                        "nextCursor": pag.get("nextCursor"),
                        "nextPage": pag.get("nextPage"),
                    }
                    
                    output_data = {
                        "transactionalEmails": transformed_emails,
                        "pagination": pagination,
                    }
                    
                    return ToolResult(
                        success=True,
                        output=json.dumps(output_data),
                        data=output_data,
                    )
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
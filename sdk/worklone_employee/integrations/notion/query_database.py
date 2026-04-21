from typing import Any, Dict
import httpx
import json
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class NotionQueryDatabaseTool(BaseTool):
    name = "notion_query_database"
    description = "Query and filter Notion database entries with advanced filtering"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="NOTION_ACCESS_TOKEN",
                description="Access token",
                env_var="NOTION_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "notion",
            context=context,
            context_token_keys=("provider_token",),
            env_token_keys=("NOTION_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "databaseId": {
                    "type": "string",
                    "description": "The UUID of the Notion database to query",
                },
                "filter": {
                    "type": "string",
                    "description": "Filter conditions as JSON (optional)",
                },
                "sorts": {
                    "type": "string",
                    "description": "Sort criteria as JSON array (optional)",
                },
                "pageSize": {
                    "type": "number",
                    "description": "Number of results to return (default: 100, max: 100)",
                },
            },
            "required": ["databaseId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        try:
            body: dict = {}
            if parameters.get("filter"):
                body["filter"] = json.loads(parameters["filter"])
            if parameters.get("sorts"):
                body["sorts"] = json.loads(parameters["sorts"])
            if parameters.get("pageSize") is not None:
                body["page_size"] = min(int(float(parameters["pageSize"])), 100)
        except json.JSONDecodeError as e:
            return ToolResult(success=False, output="", error=f"Invalid JSON in filter or sorts: {str(e)}")
        except (ValueError, TypeError) as e:
            return ToolResult(success=False, output="", error=f"Invalid parameter value: {str(e)}")
        
        url = f"https://api.notion.com/v1/databases/{parameters['databaseId']}/query"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement
from backend.lib.oauth.oauth_common import resolve_oauth_connection, refresh_oauth_access_token

class NotionAddDatabaseRowTool(BaseTool):
    name = "Add Notion Database Row"
    description = "Add a new row to a Notion database with specified properties"
    category = "integration"

    @staticmethod
    def _is_placeholder_token(value: str) -> bool:
        normalized = (value or "").strip().lower()
        return not normalized or normalized.startswith("your-") or "replace-me" in normalized or normalized == "ya29...."

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="NOTION_ACCESS_TOKEN",
                description="Notion OAuth access token",
                env_var="NOTION_ACCESS_TOKEN",
                required=True,
                auth_type="oauth",
            )
        ]

    async def _resolve_access_token(self, context: dict | None) -> str:
        connection = await resolve_oauth_connection(
            "notion",
            context=context,
            context_token_keys=("notion_token",),
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
                    "description": "ID of the database to add the row to",
                },
                "properties": {
                    "type": "object",
                    "description": 'Row properties as JSON object matching the database schema (e.g., {"Name": {"title": [{"text": {"content": "Task 1"}}]}, "Status": {"select": {"name": "Done"}}})',
                },
            },
            "required": ["databaseId", "properties"],
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
        
        url = "https://api.notion.com/v1/pages"
        
        body = {
            "parent": {
                "type": "database_id",
                "database_id": parameters["databaseId"],
            },
            "properties": parameters["properties"],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    data = response.json()
                    row_title = "Untitled"
                    properties = data.get("properties", {})
                    for prop_value in properties.values():
                        if isinstance(prop_value, dict) and prop_value.get("type") == "title" and prop_value.get("title"):
                            row_title = "".join(t.get("plain_text", "") for t in prop_value["title"] if isinstance(t, dict))
                            break
                    transformed = {
                        "id": data["id"],
                        "url": data["url"],
                        "title": row_title,
                        "created_time": data["created_time"],
                        "last_edited_time": data["last_edited_time"],
                    }
                    return ToolResult(success=True, output=str(transformed), data=transformed)
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
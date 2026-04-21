from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class NotionCreateDatabaseTool(BaseTool):
    name = "notion_create_database"
    description = "Create a new database in Notion with custom properties"
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
            context_token_keys=("accessToken",),
            env_token_keys=("NOTION_ACCESS_TOKEN",),
            placeholder_predicate=self._is_placeholder_token,
            allow_refresh=True,
        )
        return connection.access_token

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "parentId": {
                    "type": "string",
                    "description": "ID of the parent page where the database will be created",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the new database",
                },
                "properties": {
                    "type": "object",
                    "description": "Database properties as JSON object (optional, will create a default \"Name\" property if empty)",
                },
            },
            "required": ["parentId", "title"],
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
        
        properties_input = parameters.get("properties")
        if isinstance(properties_input, dict) and len(properties_input) > 0:
            body_properties = properties_input
        else:
            body_properties = {"Name": {"title": {}}}
        
        body = {
            "parent": {
                "type": "page_id",
                "page_id": parameters["parentId"],
            },
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": parameters["title"],
                    },
                },
            ],
            "properties": body_properties,
        }
        
        url = "https://api.notion.com/v1/databases"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class NotionCreatePageTool(BaseTool):
    name = "notion_create_page"
    description = "Create a new page in Notion"
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
                    "description": "The UUID of the parent Notion page where this page will be created",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the new page",
                },
                "content": {
                    "type": "string",
                    "description": "Optional content to add to the page upon creation",
                },
            },
            "required": ["parentId"],
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
        
        body: Dict[str, Any] = {
            "parent": {
                "type": "page_id",
                "page_id": parameters["parentId"],
            }
        }
        
        title = parameters.get("title")
        if title:
            body["properties"] = {
                "title": {
                    "type": "title",
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": title,
                            },
                        }
                    ],
                }
            }
        else:
            body["properties"] = {}
        
        content = parameters.get("content")
        if content:
            body["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content,
                                },
                            }
                        ],
                    },
                }
            ]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=body)
                
                if response.status_code in [200, 201, 204]:
                    return ToolResult(success=True, output=response.text, data=response.json())
                else:
                    return ToolResult(success=False, output="", error=response.text)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
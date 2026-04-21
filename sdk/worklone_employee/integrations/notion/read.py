from typing import Any, Dict
import httpx
from worklone_employee.tools.base import BaseTool, ToolResult, CredentialRequirement


class NotionReadTool(BaseTool):
    name = "notion_read"
    description = "Read content from a Notion page"
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
                "pageId": {
                    "type": "string",
                    "description": "The UUID of the Notion page to read",
                },
            },
            "required": ["pageId"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        access_token = await self._resolve_access_token(context)
        
        if self._is_placeholder_token(access_token):
            return ToolResult(success=False, output="", error="Access token not configured.")
        
        page_id = parameters["pageId"]
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        url = f"https://api.notion.com/v1/pages/{page_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return ToolResult(success=False, output="", error=response.text)
                
                data = response.json()
                
                # Extract title
                page_title = "Untitled"
                properties = data.get("properties", {})
                title_prop = properties.get("title")
                if title_prop and title_prop.get("title"):
                    title_rich = title_prop["title"]
                    if isinstance(title_rich, list) and len(title_rich) > 0:
                        page_title = "".join(t.get("plain_text", "") for t in title_rich)
                
                # Fetch blocks
                blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
                blocks_response = await client.get(blocks_url, headers=headers)
                
                content = ""
                if blocks_response.status_code == 200:
                    blocks_data = blocks_response.json()
                    blocks = blocks_data.get("results", [])
                    content_lines = []
                    
                    def rich_text_to_plain(rt_key: str) -> str:
                        rich_text = block.get(rt_key, {}).get("rich_text", [])
                        return "".join(t.get("plain_text", "") for t in rich_text)
                    
                    for block in blocks:
                        btype = block.get("type")
                        if btype == "paragraph":
                            line = rich_text_to_plain("paragraph")
                            content_lines.append(line)
                        elif btype == "heading_1":
                            line = rich_text_to_plain("heading_1")
                            content_lines.append(f"# {line}")
                        elif btype == "heading_2":
                            line = rich_text_to_plain("heading_2")
                            content_lines.append(f"## {line}")
                        elif btype == "heading_3":
                            line = rich_text_to_plain("heading_3")
                            content_lines.append(f"### {line}")
                        elif btype == "bulleted_list_item":
                            line = rich_text_to_plain("bulleted_list_item")
                            content_lines.append(f"• {line}")
                        elif btype == "numbered_list_item":
                            line = rich_text_to_plain("numbered_list_item")
                            content_lines.append(f"1. {line}")
                        elif btype == "to_do":
                            checked = "[x]" if block["to_do"].get("checked", False) else "[ ]"
                            line = rich_text_to_plain("to_do")
                            content_lines.append(f"{checked} {line}")
                    
                    content_lines = [line for line in content_lines if line]
                    content = "\n\n".join(content_lines)
                
                output_data = {
                    "content": content,
                    "title": page_title,
                    "url": data.get("url", ""),
                    "created_time": data.get("created_time", ""),
                    "last_edited_time": data.get("last_edited_time", ""),
                }
                
                return ToolResult(success=True, output=content, data=output_data)
                    
        except Exception as e:
            return ToolResult(success=False, output="", error=f"API error: {str(e)}")
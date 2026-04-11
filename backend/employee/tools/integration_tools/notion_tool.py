"""
Notion Tool — Documentation, roadmaps, and PRDs.
"""

import os
import json
import httpx
from typing import Any, Optional
from backend.employee.tools.system_tools.base import BaseTool, ToolResult, CredentialRequirement


class NotionTool(BaseTool):
    """
    Notion integration for product documentation.
    
    Supports:
    - Creating and updating pages
    - Querying databases (roadmaps, feature lists)
    - Adding content to existing pages
    - Searching across workspace
    """
    
    name = "notion"
    description = "Create and manage Notion pages for PRDs, roadmaps, and product documentation"
    category = "documentation"
    
    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="NOTION_API_TOKEN",
                description="Notion integration token",
                env_var="NOTION_API_TOKEN",
                required=True,
                example="secret_xxxxxxxxxxxxxxxxxxxxxxx",
                auth_type="api_key",
                docs_url="https://www.notion.so/my-integrations",
            ),
        ]
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": [
                        "create_page",
                        "update_page",
                        "get_page",
                        "query_database",
                        "add_to_page",
                        "search",
                    ],
                },
                # Page creation params
                "parent_id": {
                    "type": "string",
                    "description": "Parent page or database ID",
                },
                "title": {
                    "type": "string",
                    "description": "Page title",
                },
                "content": {
                    "type": "string",
                    "description": "Page content (markdown-style)",
                },
                # Page ID for updates/retrieval
                "page_id": {
                    "type": "string",
                    "description": "Notion page ID",
                },
                # Database params
                "database_id": {
                    "type": "string",
                    "description": "Database ID to query",
                },
                "filter": {
                    "type": "object",
                    "description": "Filter criteria for database query",
                },
                # Search params
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
            },
            "required": ["action"],
        }
    
    def _get_token(self, context: dict = None) -> str:
        """Get Notion API token."""
        token = os.getenv("NOTION_API_TOKEN", "")
        if context and "notion_token" in context:
            token = context["notion_token"]
        return token
    
    def _get_headers(self, token: str) -> dict:
        """Get authentication headers."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
    
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        action = parameters.get("action")
        token = self._get_token(context)
        
        if not token:
            return ToolResult(
                success=False,
                output="",
                error="Notion API token not configured. Please set NOTION_API_TOKEN.",
            )
        
        headers = self._get_headers(token)
        
        try:
            if action == "create_page":
                return await self._create_page(parameters, headers)
            elif action == "update_page":
                return await self._update_page(parameters, headers)
            elif action == "get_page":
                return await self._get_page(parameters, headers)
            elif action == "query_database":
                return await self._query_database(parameters, headers)
            elif action == "add_to_page":
                return await self._add_to_page(parameters, headers)
            elif action == "search":
                return await self._search(parameters, headers)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown action: {action}",
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Notion API error: {str(e)}",
            )
    
    async def _create_page(self, params: dict, headers: dict) -> ToolResult:
        """Create a new Notion page."""
        parent_id = params.get("parent_id")
        title = params.get("title")
        content = params.get("content", "")
        
        if not parent_id or not title:
            return ToolResult(
                success=False,
                output="",
                error="parent_id and title are required",
            )
        
        # Build page data
        page_data = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}],
                }
            },
        }
        
        # Add content blocks if provided
        if content:
            page_data["children"] = self._convert_content_to_blocks(content)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=page_data,
            )
            
            if response.status_code == 200:
                data = response.json()
                page_id = data.get("id")
                url = data.get("url")
                return ToolResult(
                    success=True,
                    output=f"Created page: {title}\nURL: {url}",
                    data={"page_id": page_id, "url": url},
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to create page: {response.text}",
                )
    
    async def _update_page(self, params: dict, headers: dict) -> ToolResult:
        """Update a Notion page."""
        page_id = params.get("page_id")
        title = params.get("title")
        
        if not page_id:
            return ToolResult(
                success=False,
                output="",
                error="page_id is required",
            )
        
        properties = {}
        if title:
            properties["title"] = {
                "title": [{"text": {"content": title}}],
            }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=headers,
                json={"properties": properties},
            )
            
            if response.status_code == 200:
                return ToolResult(
                    success=True,
                    output=f"Updated page: {page_id}",
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to update page: {response.text}",
                )
    
    async def _get_page(self, params: dict, headers: dict) -> ToolResult:
        """Get a Notion page's details."""
        page_id = params.get("page_id")
        
        if not page_id:
            return ToolResult(
                success=False,
                output="",
                error="page_id is required",
            )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                properties = data.get("properties", {})
                
                # Extract title
                title_prop = properties.get("title", {})
                title = ""
                if title_prop and "title" in title_prop:
                    title = "".join(t.get("plain_text", "") for t in title_prop["title"])
                
                return ToolResult(
                    success=True,
                    output=f"Page: {title}\nID: {page_id}",
                    data=data,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to get page: {response.text}",
                )
    
    async def _query_database(self, params: dict, headers: dict) -> ToolResult:
        """Query a Notion database."""
        database_id = params.get("database_id")
        filter_criteria = params.get("filter")
        
        if not database_id:
            return ToolResult(
                success=False,
                output="",
                error="database_id is required",
            )
        
        query_data = {}
        if filter_criteria:
            query_data["filter"] = filter_criteria
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api.notion.com/v1/databases/{database_id}/query",
                headers=headers,
                json=query_data,
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                output = f"Found {len(results)} items:\n\n"
                for item in results[:10]:  # Limit output
                    properties = item.get("properties", {})
                    # Try to get name/title
                    name = "Untitled"
                    if "Name" in properties:
                        name_data = properties["Name"]
                        if "title" in name_data:
                            name = "".join(t.get("plain_text", "") for t in name_data["title"])
                    
                    output += f"• {name}\n"
                
                if len(results) > 10:
                    output += f"\n... and {len(results) - 10} more"
                
                return ToolResult(
                    success=True,
                    output=output,
                    data=results,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Query failed: {response.text}",
                )
    
    async def _add_to_page(self, params: dict, headers: dict) -> ToolResult:
        """Add content blocks to an existing page."""
        page_id = params.get("page_id")
        content = params.get("content")
        
        if not page_id or not content:
            return ToolResult(
                success=False,
                output="",
                error="page_id and content are required",
            )
        
        blocks = self._convert_content_to_blocks(content)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=headers,
                json={"children": blocks},
            )
            
            if response.status_code == 200:
                return ToolResult(
                    success=True,
                    output=f"Added content to page: {page_id}",
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to add content: {response.text}",
                )
    
    async def _search(self, params: dict, headers: dict) -> ToolResult:
        """Search Notion workspace."""
        query = params.get("query", "")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json={"query": query, "page_size": 10},
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                output = f"Search results for '{query}':\n\n"
                for item in results:
                    item_type = item.get("object")  # page or database
                    
                    if item_type == "page":
                        properties = item.get("properties", {})
                        title = "Untitled"
                        if "title" in properties:
                            title = "".join(t.get("plain_text", "") for t in properties["title"].get("title", []))
                        output += f"📄 {title}\n"
                    
                    elif item_type == "database":
                        title = item.get("title", [{}])[0].get("plain_text", "Untitled")
                        output += f"🗃️  {title} (Database)\n"
                
                return ToolResult(
                    success=True,
                    output=output,
                    data=results,
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Search failed: {response.text}",
                )
    
    def _convert_content_to_blocks(self, content: str) -> list:
        """Convert markdown-style content to Notion blocks."""
        blocks = []
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Heading detection
            if line.startswith("# "):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    },
                })
            elif line.startswith("## "):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    },
                })
            elif line.startswith("### "):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    },
                })
            elif line.startswith("- ") or line.startswith("* "):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    },
                })
            elif line[0:2].strip().isdigit() and "." in line[:4]:
                # Numbered list
                text = line.split(".", 1)[1].strip()
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": text}}]
                    },
                })
            else:
                # Regular paragraph
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": line}}]
                    },
                })
        
        return blocks

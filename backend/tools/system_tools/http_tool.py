"""
HTTP Tool — Make arbitrary HTTP requests.
"""

from typing import Any
import httpx
from backend.tools.system_tools.base import BaseTool, ToolResult


class HTTPTool(BaseTool):
    """Make HTTP requests to any endpoint."""
    
    name = "http_request"
    description = "Make an HTTP request to any URL. Use for calling APIs, webhooks, or web services."
    category = "core"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, PUT, PATCH, DELETE)",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                },
                "url": {
                    "type": "string",
                    "description": "The URL to request",
                },
                "headers": {
                    "type": "object",
                    "description": "HTTP headers as key-value pairs",
                },
                "body": {
                    "type": "object",
                    "description": "Request body (for POST/PUT/PATCH)",
                },
                "query_params": {
                    "type": "object",
                    "description": "Query parameters as key-value pairs",
                },
            },
            "required": ["method", "url"],
        }
    
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        method = parameters.get("method", "GET")
        url = parameters.get("url")
        headers = parameters.get("headers", {})
        body = parameters.get("body")
        query_params = parameters.get("query_params")
        
        if not url:
            return ToolResult(
                success=False,
                output="",
                error="URL is required",
            )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body,
                    params=query_params,
                )
                
                try:
                    response_data = response.json()
                except Exception:
                    response_data = response.text
                
                output = f"Status: {response.status_code}\nResponse: {response_data}"
                
                return ToolResult(
                    success=200 <= response.status_code < 300,
                    output=output,
                    data=response_data,
                    error="" if response.status_code < 400 else response.text,
                )
        
        except httpx.RequestError as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Request failed: {str(e)}",
            )

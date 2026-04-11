"""
HTTP Block Handler — makes HTTP requests from blocks.
"""

import time
import httpx
from backend.workflows.types import Block
from backend.workflows.engine.handlers.base import BaseBlockHandler
from backend.workflows.logger import get_logger

logger = get_logger("http_handler")


class HTTPBlockHandler(BaseBlockHandler):
    """Execute an HTTP request block."""
    
    async def handle(self, block: Block) -> dict:
        config = block.config
        
        method = config.method or config.params.get("method", "GET")
        url = config.url or config.params.get("url", "")
        headers = config.params.get("headers", {})
        body = config.params.get("body")
        query_params = config.params.get("query_params")
        
        # Resolve templates
        url = self.resolver.resolve(url)
        headers = self.resolver.resolve(headers) if headers else {}
        body = self.resolver.resolve(body) if body else None
        query_params = self.resolver.resolve(query_params) if query_params else None
        
        if not url:
            return {
                "success": False,
                "error": "No URL provided",
            }
        
        start = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    json=body,
                    params=query_params,
                )
                
                elapsed = time.time() - start
                
                try:
                    data = response.json()
                except Exception:
                    data = response.text
                
                return {
                    "success": 200 <= response.status_code < 300,
                    "status_code": response.status_code,
                    "data": data,
                    "output": str(data),
                    "execution_time": elapsed,
                }
        
        except Exception as e:
            logger.exception(f"HTTP block '{block.id}' failed")
            return {
                "success": False,
                "error": f"HTTP request failed: {str(e)}",
                "output": "",
            }

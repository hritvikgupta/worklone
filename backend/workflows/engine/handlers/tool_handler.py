"""
Tool Block Handler — executes a registered tool.
"""

import time
from backend.workflows.types import Block
from backend.workflows.engine.handlers.base import BaseBlockHandler
from backend.workflows.tools.registry import registry
from backend.workflows.logger import get_logger

logger = get_logger("tool_handler")


class ToolBlockHandler(BaseBlockHandler):
    """Execute a tool block."""
    
    async def handle(self, block: Block) -> dict:
        config = block.config
        tool_name = config.tool_name or config.params.get("tool")
        
        if not tool_name:
            return {
                "success": False,
                "error": "No tool specified",
            }
        
        # Get params and resolve variables
        params = self.get_resolved_params(block)
        # Remove tool name from params (it's in config)
        params.pop("tool", None)
        
        start = time.time()
        
        try:
            result = await registry.execute(
                tool_name,
                parameters=params,
                context=self.context,
            )
            
            elapsed = time.time() - start
            
            return {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "data": result.data,
                "execution_time": elapsed,
            }
        
        except Exception as e:
            logger.exception(f"Tool block '{block.id}' failed")
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "output": "",
            }

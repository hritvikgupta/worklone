"""
Function Block Handler — executes Python code blocks.
"""

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from backend.workflows.types import Block
from backend.workflows.engine.handlers.base import BaseBlockHandler
from backend.workflows.logger import get_logger

logger = get_logger("function_handler")


class FunctionBlockHandler(BaseBlockHandler):
    """Execute a Python code block."""
    
    async def handle(self, block: Block) -> dict:
        config = block.config
        code = config.code or config.params.get("code", "")
        
        if not code:
            return {
                "success": False,
                "error": "No code provided",
            }
        
        # Resolve code templates
        code = self.resolver.resolve(code)
        
        # Build namespace with context and variables
        namespace = {
            "context": self.context,
            "variables": self.resolver.variables,
            "result": None,
        }
        
        start = time.time()
        
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                await loop.run_in_executor(
                    executor,
                    self._execute_code,
                    code,
                    namespace,
                )
            
            elapsed = time.time() - start
            result = namespace.get("result")
            
            return {
                "success": True,
                "result": result,
                "output": str(result) if result is not None else "Executed successfully",
                "execution_time": elapsed,
            }
        
        except Exception as e:
            logger.exception(f"Function block '{block.id}' failed")
            return {
                "success": False,
                "error": f"Code execution failed: {str(e)}",
                "output": "",
            }
    
    def _execute_code(self, code: str, namespace: dict):
        """Execute code in namespace."""
        exec(code, namespace)

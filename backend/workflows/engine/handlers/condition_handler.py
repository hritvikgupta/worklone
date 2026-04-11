"""
Condition Block Handler — evaluates conditions and branches.
"""

import time
from backend.workflows.types import Block
from backend.workflows.engine.handlers.base import BaseBlockHandler
from backend.workflows.utils import evaluate_condition
from backend.workflows.logger import get_logger

logger = get_logger("condition_handler")


class ConditionBlockHandler(BaseBlockHandler):
    """Evaluate a condition and return true/false."""
    
    async def handle(self, block: Block) -> dict:
        config = block.config
        condition = config.condition or config.params.get("condition", "")
        
        if not condition:
            return {
                "success": True,
                "result": True,
                "condition": "",
                "evaluated": True,
            }
        
        # Resolve condition templates
        condition = self.resolver.resolve(condition)
        
        start = time.time()
        
        try:
            result = evaluate_condition(condition, self.resolver.get_context())
            elapsed = time.time() - start
            
            logger.info(f"Condition '{condition}' evaluated to: {result}")
            
            return {
                "success": True,
                "result": result,
                "condition": condition,
                "evaluated": result,
                "execution_time": elapsed,
            }
        
        except Exception as e:
            logger.exception(f"Condition block '{block.id}' failed")
            return {
                "success": False,
                "error": f"Condition evaluation failed: {str(e)}",
                "result": False,
            }

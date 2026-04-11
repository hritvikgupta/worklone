"""
Base Block Handler — interface for all block handlers.
"""

from abc import ABC, abstractmethod
from typing import Any
from backend.workflows.types import Block, ExecutionResult
from backend.workflows.engine.variable_resolver import VariableResolver
from backend.workflows.logger import get_logger

logger = get_logger("block_handler")


class BaseBlockHandler(ABC):
    """Base class for all block handlers."""
    
    def __init__(self, resolver: VariableResolver, context: dict = None):
        self.resolver = resolver
        self.context = context or {}
    
    @abstractmethod
    async def handle(self, block: Block) -> dict:
        """
        Execute the block and return its output.
        
        Args:
            block: The block to execute
        
        Returns:
            dict: The output of the block execution
        """
        pass
    
    def get_resolved_params(self, block: Block) -> dict:
        """Get block params with all variables resolved."""
        params = dict(block.config.params)
        return self.resolver.resolve(params)
    
    def get_resolved_body(self, block: Block) -> dict:
        """Get block body with all variables resolved."""
        body = dict(block.config.body)
        return self.resolver.resolve(body)


class NoOpBlockHandler(BaseBlockHandler):
    """Handler for START/END blocks — does nothing, just passes through."""
    
    async def handle(self, block: Block) -> dict:
        return {
            "success": True,
            "output": f"{block.config.block_type.value} block passed",
            "execution_time": 0.0,
        }

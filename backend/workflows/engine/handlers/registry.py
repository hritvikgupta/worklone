"""
Handler Registry — maps block types to handlers.
"""

from backend.workflows.types import BlockType
from backend.workflows.engine.handlers.base import BaseBlockHandler
from backend.workflows.logger import get_logger

logger = get_logger("handler_registry")


class HandlerRegistry:
    """Registry mapping block types to their handlers."""
    
    def __init__(self):
        self._handlers: dict[BlockType, type] = {}
    
    def register(self, block_type: BlockType, handler_class: type) -> None:
        """Register a handler for a block type."""
        self._handlers[block_type] = handler_class
        logger.debug(f"Registered handler for {block_type.value}")
    
    def get_handler(self, block_type: BlockType, **kwargs) -> BaseBlockHandler:
        """Get a handler instance for a block type."""
        handler_class = self._handlers.get(block_type)
        if not handler_class:
            # Fall back to generic handler
            from backend.workflows.engine.handlers.tool_handler import ToolBlockHandler
            logger.warning(f"No handler for {block_type.value}, using tool handler")
            return ToolBlockHandler(**kwargs)
        return handler_class(**kwargs)
    
    def has_handler(self, block_type: BlockType) -> bool:
        return block_type in self._handlers


# Global registry
handler_registry = HandlerRegistry()


def register_handler(block_type: BlockType, handler_class: type) -> None:
    """Convenience function to register a handler."""
    handler_registry.register(block_type, handler_class)


def get_handler(block_type: BlockType, **kwargs) -> BaseBlockHandler:
    """Convenience function to get a handler."""
    return handler_registry.get_handler(block_type, **kwargs)


# Register all handlers
def register_all_handlers():
    """Register all built-in handlers."""
    from backend.workflows.engine.handlers.agent_handler import AgentBlockHandler
    from backend.workflows.engine.handlers.tool_handler import ToolBlockHandler
    from backend.workflows.engine.handlers.function_handler import FunctionBlockHandler
    from backend.workflows.engine.handlers.condition_handler import ConditionBlockHandler
    from backend.workflows.engine.handlers.http_handler import HTTPBlockHandler
    from backend.workflows.engine.handlers.base import NoOpBlockHandler
    
    handler_registry.register(BlockType.AGENT, AgentBlockHandler)
    handler_registry.register(BlockType.TOOL, ToolBlockHandler)
    handler_registry.register(BlockType.FUNCTION, FunctionBlockHandler)
    handler_registry.register(BlockType.CONDITION, ConditionBlockHandler)
    handler_registry.register(BlockType.HTTP, HTTPBlockHandler)
    # START and END are no-ops
    handler_registry.register(BlockType.START, NoOpBlockHandler)
    handler_registry.register(BlockType.END, NoOpBlockHandler)
    
    logger.info("All block handlers registered")

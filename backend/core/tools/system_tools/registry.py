"""
Tool Registry — manages all available tools.
"""

from typing import Optional
import re
from backend.core.tools.system_tools.base import BaseTool
from backend.core.logging import get_logger

logger = get_logger("registry")


class ToolRegistry:
    """Central registry of all available tools."""
    
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        # Maps OpenAI-safe function names back to actual registry tool names.
        self._openai_name_map: dict[str, str] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def unregister(self, name: str) -> Optional[BaseTool]:
        """Remove and return a tool."""
        return self._tools.pop(name, None)
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def has(self, name: str) -> bool:
        """Check if a tool exists."""
        return name in self._tools
    
    def list_tools(self) -> list[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def list_names(self) -> list[str]:
        """List all tool names."""
        return list(self._tools.keys())
    
    def list_by_category(self, category: str) -> list[BaseTool]:
        """List tools by category."""
        return [t for t in self._tools.values() if t.category == category]
    
    def list_categories(self) -> list[str]:
        """List all categories."""
        return list(set(t.category for t in self._tools.values()))
    
    def to_openai_tools(self) -> list[dict]:
        """Return all tools in OpenAI format."""
        self._openai_name_map = {}
        seen_names: set[str] = set()
        schemas: list[dict] = []

        for tool in self._tools.values():
            schema = tool.to_openai_schema()
            function = schema.get("function") or {}
            raw_name = str(function.get("name") or tool.name or "")
            safe_name = self._to_openai_safe_name(raw_name)

            # Ensure uniqueness after normalization.
            if safe_name in seen_names:
                base = safe_name
                i = 2
                while f"{base}_{i}" in seen_names:
                    i += 1
                safe_name = f"{base}_{i}"
            seen_names.add(safe_name)

            function["name"] = safe_name
            schema["function"] = function
            self._openai_name_map[safe_name] = raw_name
            schemas.append(schema)

        return schemas
    
    def to_react_descriptions(self) -> str:
        """Return ReAct-style tool descriptions."""
        return "\n".join(t.to_react_description() for t in self._tools.values())
    
    async def execute(
        self,
        name: str,
        parameters: dict = None,
        context: dict = None,
    ):
        """Execute a tool by name."""
        resolved_name = self._openai_name_map.get(name, name)
        tool = self.get(resolved_name)
        if not tool:
            from backend.core.tools.system_tools.base import ToolResult
            return ToolResult(
                success=False,
                output=f"",
                error=f"Tool '{name}' not found. Available: {', '.join(self.list_names())}",
            )
        
        try:
            result = await tool.execute(parameters or {}, context)
            return result
        except Exception as e:
            from backend.core.tools.system_tools.base import ToolResult
            return ToolResult(
                success=False,
                output=f"",
                error=f"Error executing '{resolved_name}': {str(e)}",
            )

    @staticmethod
    def _to_openai_safe_name(name: str) -> str:
        """Normalize function names to OpenAI's allowed pattern: ^[a-zA-Z0-9_-]+$."""
        candidate = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
        return candidate or "tool"


# Global registry instance
registry = ToolRegistry()


def register_tool(tool: BaseTool) -> None:
    """Convenience function to register a tool."""
    registry.register(tool)


def get_tool(name: str) -> Optional[BaseTool]:
    """Convenience function to get a tool."""
    return registry.get(name)


async def execute_tool(name: str, parameters: dict = None, context: dict = None):
    """Convenience function to execute a tool."""
    return await registry.execute(name, parameters, context)

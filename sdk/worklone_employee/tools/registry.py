"""
Tool Registry — manages all available tools.
"""

from typing import Optional
import re

from worklone_employee.tools.base import BaseTool, ToolResult
from worklone_employee.logging.logger import get_logger

logger = get_logger("registry")


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._openai_name_map: dict[str, str] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> Optional[BaseTool]:
        return self._tools.pop(name, None)

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def list_by_category(self, category: str) -> list[BaseTool]:
        return [t for t in self._tools.values() if t.category == category]

    def list_categories(self) -> list[str]:
        return list(set(t.category for t in self._tools.values()))

    def to_openai_tools(self) -> list[dict]:
        self._openai_name_map = {}
        seen_names: set[str] = set()
        schemas: list[dict] = []
        for tool in self._tools.values():
            schema = tool.to_openai_schema()
            function = schema.get("function") or {}
            raw_name = str(function.get("name") or tool.name or "")
            safe_name = self._to_openai_safe_name(raw_name)
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
        return "\n".join(t.to_react_description() for t in self._tools.values())

    async def execute(self, name: str, parameters: dict = None, context: dict = None):
        resolved_name = self._openai_name_map.get(name, name)
        tool = self.get(resolved_name)
        if not tool:
            return ToolResult(
                success=False, output="",
                error=f"Tool '{name}' not found. Available: {', '.join(self.list_names())}",
            )
        try:
            return await tool.execute(parameters or {}, context)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Error executing '{resolved_name}': {str(e)}")

    @staticmethod
    def _to_openai_safe_name(name: str) -> str:
        candidate = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
        return candidate or "tool"


registry = ToolRegistry()


def register_tool(tool: BaseTool) -> None:
    registry.register(tool)


def get_tool(name: str) -> Optional[BaseTool]:
    return registry.get(name)


async def execute_tool(name: str, parameters: dict = None, context: dict = None):
    return await registry.execute(name, parameters, context)

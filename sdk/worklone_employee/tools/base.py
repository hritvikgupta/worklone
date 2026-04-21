"""
Base Tool Interface for the worklone_employee SDK.
All tools must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CredentialRequirement:
    key: str
    description: str
    env_var: str
    required: bool = True
    example: str = ""
    auth_type: str = "manual"
    auth_url: str = ""
    auth_provider: str = ""
    auth_scopes: str = ""


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str = ""
    data: Any = None

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output, "error": self.error, "data": self.data}

    def to_observation(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error or self.output}"


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    category: str = "general"

    @abstractmethod
    def get_schema(self) -> dict:
        pass

    @abstractmethod
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        pass

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_schema(),
            },
        }

    def get_required_credentials(self) -> list[CredentialRequirement]:
        return []

    def to_react_description(self) -> str:
        schema = self.get_schema()
        props = schema.get("properties", {})
        required = schema.get("required", [])
        params_str = ", ".join(
            f"{k}: {v.get('type', 'any')}{'*' if k in required else ''}"
            for k, v in props.items()
        )
        return f"{self.name}: {self.description} ({params_str})"

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"

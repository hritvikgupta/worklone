"""
Base Tool Interface for the workflow engine.

All tools must implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CredentialRequirement:
    """Describes a credential a tool needs to function."""
    key: str                # e.g. "SLACK_BOT_TOKEN"
    description: str        # e.g. "Slack Bot OAuth token (xoxb-...)"
    env_var: str            # environment variable name to check
    required: bool = True   # False = optional credential
    example: str = ""       # e.g. "xoxb-1234-5678-abc"
    auth_type: str = "manual"  # "oauth", "api_key", "manual"
    auth_url: str = ""      # OAuth redirect URL (for auth_type="oauth")
    auth_provider: str = "" # "google", "slack", "github", etc.
    auth_scopes: str = ""   # OAuth scopes needed


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    output: str
    error: str = ""
    data: Any = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "data": self.data,
        }

    def to_observation(self) -> str:
        """Format result as an observation for ReAct loops."""
        if self.success:
            return self.output
        return f"Error: {self.error or self.output}"


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    """

    name: str = ""
    description: str = ""
    category: str = "general"
    
    @abstractmethod
    def get_schema(self) -> dict:
        """
        Return JSON Schema for tool parameters.
        
        Example:
        {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to send"},
                "channel": {"type": "string", "description": "Slack channel"}
            },
            "required": ["message"]
        }
        """
        pass
    
    @abstractmethod
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            parameters: Tool parameters from LLM or workflow
            context: Execution context (workflow variables, etc.)
        
        Returns:
            ToolResult with success status and output
        """
        pass
    
    def to_openai_schema(self) -> dict:
        """Return OpenAI-compatible tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_schema(),
            },
        }
    
    def get_required_credentials(self) -> list[CredentialRequirement]:
        """
        Return credentials this tool needs to function.
        Override in subclasses that require authentication.
        Default: no credentials needed.
        """
        return []

    def to_react_description(self) -> str:
        """Return ReAct-style tool description."""
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

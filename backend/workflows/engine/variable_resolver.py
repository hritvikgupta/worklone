"""
Variable Resolver — resolves {{block.output}} and workflow variables.

Supports:
- {{variable}} — workflow variable
- {{block_id.output.field}} — block output
- {{_triggerInput.field}} — trigger input data
- {{_triggerType}} — what started the workflow
"""

from backend.workflows.types import Block, Workflow
from backend.workflows.logger import get_logger

logger = get_logger("variable_resolver")


class VariableResolver:
    """Resolves variable references in workflow blocks."""
    
    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        self.variables: dict = dict(workflow.variables)
        self.block_outputs: dict[str, dict] = {}
    
    def set_variable(self, key: str, value) -> None:
        self.variables[key] = value
    
    def get_variable(self, key: str, default=None):
        return self.variables.get(key, default)
    
    def store_output(self, block_id: str, output: dict) -> None:
        self.block_outputs[block_id] = output
        logger.debug(f"Stored output for {block_id}: {list(output.keys())}")
    
    def resolve(self, value) -> any:
        """Resolve all variable references in a value (recursive for dict/list)."""
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item) for item in value]
        return value
    
    def _resolve_string(self, text: str) -> str:
        """Resolve {{}} references in a string."""
        import re
        
        def replacer(match):
            key = match.group(1).strip()
            val = self._get_value(key)
            return str(val) if val is not None else ""
        
        return re.sub(r"\{\{(.+?)\}\}", replacer, text)
    
    def _get_value(self, key: str):
        """
        Get value for a key.
        
        Resolution order:
        1. block_id.output.field
        2. block_id.result
        3. workflow variable
        4. Special: _triggerInput, _triggerType
        """
        parts = key.split(".")
        
        # Special variables
        if key == "_triggerInput":
            return self.variables.get("_triggerInput")
        if key == "_triggerType":
            return self.variables.get("_triggerType")
        
        # Block output access: block_id.output.field
        if parts[0] in self.block_outputs:
            block_output = self.block_outputs[parts[0]]
            if len(parts) == 1:
                return block_output
            # Navigate into output
            value = block_output
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        
        # Workflow variables
        if len(parts) == 1 and parts[0] in self.variables:
            return self.variables[parts[0]]
        
        # Nested variable access
        value = self.variables
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value
    
    def get_context(self) -> dict:
        """Get the full resolution context."""
        return {
            **self.variables,
            **{f"{bid}.output": out for bid, out in self.block_outputs.items()},
        }
    
    def to_dict(self) -> dict:
        return {
            "variables": self.variables,
            "block_outputs": self.block_outputs,
        }
    
    @classmethod
    def from_dict(cls, workflow: Workflow, data: dict) -> "VariableResolver":
        resolver = cls(workflow)
        resolver.variables = data.get("variables", {})
        resolver.block_outputs = data.get("block_outputs", {})
        return resolver

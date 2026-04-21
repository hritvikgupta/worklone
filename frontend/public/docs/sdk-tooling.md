# SDK Tooling Guide

Learn how to extend your AI employee's capabilities using the Worklone Tooling system.

## Built-in Tools

The SDK comes with a vast catalog of pre-built tools. You can enable them by name:

```python
emp.use_tools(["web_search", "http_request", "gmail", "slack"])
```

### Tool Categories
- **System Tools**: Web search, file manipulation, shell access, HTTP requests.
- **Integration Tools**: 250+ connectors for SaaS apps (GitHub, HubSpot, Linear, etc.).
- **Specialized Tools**: Tools tailored for specific roles (PM, Engineer, Analyst, etc.).

## Custom Tools

You can add your own logic to the employee in two ways.

### 1. Using the `@emp.tool` Decorator (Recommended)
The SDK automatically introspects your function's type hints to generate the JSON schema required by the LLM.

```python
@emp.tool(description="Calculate the ROI for a given investment")
def calculate_roi(investment: float, return_amount: float) -> str:
    roi = ((return_amount - investment) / investment) * 100
    return f"The ROI is {roi:.2f}%"
```

### 2. Implementing `BaseTool`
For more complex tools that require state or initialization, subclass `BaseTool`.

```python
from worklone_employee.tools.base import BaseTool, ToolResult

class MyDatabaseTool(BaseTool):
    def __init__(self, connection_string):
        super().__init__()
        self.conn = connection_string

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        # Your logic here
        return ToolResult(success=True, output="Query result")

emp.add_tool(MyDatabaseTool("sqlite:///my.db"))
```

## Tool Execution Flow
1. **Reasoning**: LLM decides a tool is needed based on the user prompt.
2. **Call**: SDK executes the tool's `execute` method.
3. **Observation**: The `ToolResult` is fed back to the LLM as an observation.
4. **Iteration**: LLM decides if it has enough information or needs another tool.

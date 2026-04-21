# Tools

Tools are the actions an AI employee can take. Every tool call goes through the ReAct loop — the LLM decides when and how to call each tool based on the user's task.

## Built-in System Tools

Enable by name with `emp.use_tools()`:

```python
emp.use_tools(["web_search", "http_request", "file_operations", "run_shell"])
```

| Tool Name | What it does |
|-----------|-------------|
| `web_search` | Search the web using DuckDuckGo |
| `web_extract` | Extract content from a URL |
| `http_request` | Make arbitrary HTTP requests |
| `file_operations` | Read, write, and manage local files |
| `run_shell` | Execute shell commands |
| `run_sql` | Execute SQL queries |
| `memory_store` | Store and retrieve key-value pairs |
| `call_llm` | Call an LLM as a sub-task |
| `ask_user` | Pause and ask the user a question |
| `manage_tasks` | Create and manage a task plan |

## Custom Tools via Decorator

The `@emp.tool` decorator wraps any Python function as a tool. The SDK introspects your type hints to auto-generate the JSON schema the LLM needs.

```python
@emp.tool(description="Calculate compound interest")
def compound_interest(principal: float, rate: float, years: int) -> str:
    result = principal * (1 + rate / 100) ** years
    return f"${result:,.2f} after {years} years"
```

### Type Support

The decorator supports `str`, `int`, `float`, `bool` parameters. All are required by default unless you provide a default value.

```python
@emp.tool(description="Send a notification")
def notify(message: str, urgent: bool) -> str:
    level = "URGENT" if urgent else "INFO"
    return f"[{level}] {message} sent"
```

## Custom Tools via BaseTool

For tools that require initialization, state, or complex schemas, subclass `BaseTool`:

```python
from worklone_employee import BaseTool, ToolResult

class DatabaseTool(BaseTool):
    name = "query_database"
    description = "Run a read-only SQL query against the product database"
    category = "data"

    def __init__(self, connection_string: str):
        self.conn_str = connection_string

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL SELECT query to execute"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows to return (default: 100)"
                }
            },
            "required": ["query"]
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        query = parameters["query"]
        limit = parameters.get("limit", 100)
        try:
            # Your DB logic here
            results = f"Query executed: {query} (limit {limit})"
            return ToolResult(success=True, output=results)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

# Register it
emp.add_tool(DatabaseTool("postgresql://localhost/mydb"))
```

## ToolResult

Every tool must return a `ToolResult`:

```python
from worklone_employee import ToolResult

# Success
return ToolResult(success=True, output="Done.", data={"key": "value"})

# Failure
return ToolResult(success=False, output="", error="Connection refused")
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether the tool call succeeded |
| `output` | `str` | Text shown to the LLM as the observation |
| `error` | `str` | Error message if `success=False` |
| `data` | `Any` | Optional structured data (not shown to LLM directly) |

## Integration Tools

406 pre-built tools across 12 integrations are available via the integrations package:

```python
from worklone_employee import Gmail, Slack, Github, Stripe

gmail = Gmail(client_id="...", client_secret="...", token_store=store)
for tool in gmail.all():
    emp.add_tool(tool)

# Or add individual tools
emp.add_tool(gmail.send)
emp.add_tool(gmail.read)
emp.add_tool(gmail.search)
```

See [Integrations](/docs/integrations) for the full list.

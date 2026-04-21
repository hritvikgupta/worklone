# Employee Class Reference

## Constructor

```python
Employee(
    name: str,
    description: str = "",
    model: str = "anthropic/claude-haiku-4-5",
    temperature: float = 0.7,
    system_prompt: str = "",
    db: str = None,
    owner_id: str = "sdk_user",
    session_id: str = None,
    auto_approve: bool = False,
    role: str = "generalist",
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Employee display name |
| `description` | `str` | `""` | What this employee does |
| `model` | `str` | `"anthropic/claude-haiku-4-5"` | OpenRouter model string |
| `temperature` | `float` | `0.7` | LLM sampling temperature |
| `system_prompt` | `str` | `""` | Additional system instructions |
| `db` | `str` | `~/.worklone/sdk.db` | SQLite database path. Use `":memory:"` for no persistence |
| `owner_id` | `str` | `"sdk_user"` | User identifier — used for memory isolation and token lookup |
| `session_id` | `str` | auto-generated | Resume a specific session by ID |
| `auto_approve` | `bool` | `False` | Skip human-in-the-loop pauses |
| `role` | `str` | `"generalist"` | Determines which specialized tools are pre-loaded |

## Methods

### run

```python
emp.run(message: str) -> str
```

Run the employee synchronously. Blocks until the task completes and returns the final answer.

Cannot be called inside a running event loop — use `_arun` instead.

### _arun

```python
await emp._arun(message: str) -> str
```

Async version of `run`. Use inside `async` functions or FastAPI routes.

### stream

```python
async for token in emp.stream(message: str):
    print(token, end="")
```

Async generator that yields response tokens as they arrive.

### use_tools

```python
emp.use_tools(tool_names: list[str]) -> Employee
```

Enable built-in tools by name. Returns `self` for chaining.

```python
emp.use_tools(["web_search", "http_request", "file_operations"])
```

### tool (decorator)

```python
@emp.tool(description: str = "", name: str = None)
def my_function(param: str) -> str:
    ...
```

Register a Python function as a tool. Type hints are used to auto-generate the JSON schema.

### add_tool

```python
emp.add_tool(tool_instance: BaseTool) -> Employee
```

Add a `BaseTool` instance directly. Returns `self` for chaining.

### add_skill

```python
emp.add_skill(
    skill_name: str,
    category: str = "research",
    proficiency_level: int = 80,
    description: str = "",
) -> Employee
```

Assign a static skill to the employee — used to guide behavior without evolution.

### enable_evolution

```python
emp.enable_evolution() -> Employee
```

Turn on persistent memory and skill learning. Requires `db` and `owner_id` to be set.

### reset

```python
emp.reset() -> None
```

Clear the current session's conversation history. Evolution data (memory, skills) is preserved.

### on_approval_needed (decorator)

```python
@emp.on_approval_needed
def handle_approval(event: dict) -> dict:
    return {"approved": True}
```

Register a callback for human-in-the-loop approval events. Can be sync or async.

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `emp._employee_id` | `str` | Auto-generated unique ID for this employee instance |
| `emp._owner_id` | `str` | The `owner_id` passed at construction |
| `emp._model` | `str` | The model string |
| `emp._session_id` | `str` | The active session ID |

# Employee

The `Employee` class is the main entry point of the SDK. It represents an autonomous AI agent that can reason, use tools, and learn over time.

## Creating an Employee

```python
from worklone_employee import Employee

emp = Employee(
    name="Aria",
    description="An executive assistant that handles email and scheduling",
    model="anthropic/claude-sonnet-4-5",
    system_prompt="You are Aria, a sharp executive assistant. Always use available tools before answering.",
    owner_id="user_123",
    db="./aria.db",
)
```

## Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | required | Display name of the employee |
| `description` | `str` | `""` | What this employee does — used in multi-agent setups |
| `model` | `str` | `"anthropic/claude-haiku-4-5"` | OpenRouter model string |
| `temperature` | `float` | `0.7` | LLM temperature |
| `system_prompt` | `str` | `""` | Additional instructions appended to the base system prompt |
| `owner_id` | `str` | `"sdk_user"` | The user this employee belongs to — used for memory and token lookup |
| `db` | `str` | `~/.worklone/sdk.db` | Path to the SQLite database for sessions and evolution |
| `session_id` | `str` | auto-generated | Resume a specific conversation session |
| `auto_approve` | `bool` | `False` | Skip human-in-the-loop pauses automatically |

## Running a Task

### Synchronous

```python
result = emp.run("Summarize my inbox and flag anything urgent.")
print(result)
```

### Async

```python
result = await emp._arun("Summarize my inbox and flag anything urgent.")
```

### Streaming

```python
async for token in emp.stream("Write a market analysis for NVIDIA."):
    print(token, end="", flush=True)
```

## Adding Tools

### Built-in Tools

```python
emp.use_tools(["web_search", "http_request", "file_operations"])
```

### Custom Tools via Decorator

```python
@emp.tool(description="Get the current price of a stock ticker symbol")
def get_stock_price(ticker: str) -> str:
    prices = {"AAPL": "$189.30", "NVDA": "$875.00"}
    return prices.get(ticker.upper(), "Price not available")
```

### Integration Tools

```python
from worklone_employee import Gmail, InMemoryTokenStore

store = InMemoryTokenStore()
store.seed("user_123", "gmail", {
    "access_token": "ya29...",
    "refresh_token": "1//..."
})

gmail = Gmail(
    client_id="your_client_id",
    client_secret="your_client_secret",
    token_store=store,
)

emp = Employee(name="Aria", owner_id="user_123")
for tool in gmail.all():
    emp.add_tool(tool)
```

## Evolution

```python
emp.enable_evolution()
```

When enabled, the employee automatically:
- Extracts and saves facts about the user every 8 conversation turns
- Detects successful tool patterns and saves them as reusable skills every 10 tool calls

See [Evolution & Memory](/docs/sdk-evolution) for full details.

## Human-in-the-Loop

```python
@emp.on_approval_needed
def handle_approval(event):
    print(f"Approval needed: {event['message']}")
    user_input = input("Approve? (y/n): ")
    return {"approved": user_input.lower() == "y"}
```

## Session Management

```python
# Start a session
emp = Employee(name="Aria", db="./aria.db", session_id="session_001")
emp.run("My name is Alice.")

# Resume later — Aria remembers the conversation
emp2 = Employee(name="Aria", db="./aria.db", session_id="session_001")
emp2.run("What is my name?")
# → "Your name is Alice."
```

## Resetting

```python
emp.reset()  # Clears current conversation history, keeps evolution data
```

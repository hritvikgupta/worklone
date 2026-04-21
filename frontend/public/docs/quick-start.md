# Quick Start

Get your first AI employee running in under 5 minutes.

## Install

```bash
pip install worklone-employee
```

Requires Python 3.11+.

## Set Your LLM Provider Key

```bash
export OPENROUTER_API_KEY=sk-or-...
```

Or in Python:

```python
import os
os.environ["OPENROUTER_API_KEY"] = "sk-or-..."
```

## Create Your First Employee

```python
from worklone_employee import Employee

emp = Employee(
    name="Aria",
    description="A helpful research assistant",
    model="anthropic/claude-haiku-4-5",
)

result = emp.run("What is the capital of France?")
print(result)
# → "The capital of France is Paris."
```

## Add a Custom Tool

```python
from worklone_employee import Employee

emp = Employee(name="Aria", model="anthropic/claude-haiku-4-5")

@emp.tool(description="Look up the current price of a stock ticker")
def get_stock_price(ticker: str) -> str:
    prices = {"AAPL": "$189.30", "NVDA": "$875.00", "MSFT": "$415.50"}
    return prices.get(ticker.upper(), f"No data for {ticker}")

result = emp.run("What is NVIDIA's current stock price?")
print(result)
```

## Enable Built-in Tools

```python
emp.use_tools(["web_search", "http_request"])

result = emp.run("Search the web for the latest news about AI agents.")
print(result)
```

## Add Gmail Integration

```python
from worklone_employee import Employee, Gmail, InMemoryTokenStore

store = InMemoryTokenStore()
store.seed("user_123", "gmail", {
    "access_token": "ya29.xxx",
    "refresh_token": "1//xxx"
})

gmail = Gmail(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    client_secret="YOUR_GOOGLE_CLIENT_SECRET",
    token_store=store,
)

emp = Employee(name="Aria", owner_id="user_123")
for tool in gmail.all():
    emp.add_tool(tool)

result = emp.run("Check my inbox and summarize unread emails.")
print(result)
```

## Enable Memory

```python
emp = Employee(
    name="Aria",
    model="anthropic/claude-haiku-4-5",
    db="./aria.db",
    owner_id="user_123",
)

emp.enable_evolution()

emp.run("My name is Alice and I work in fintech.")
# Later sessions — Aria remembers Alice automatically
```

## Next Steps

- [What is Worklone](/docs/what-is-worklone) — understand the architecture
- [Employee](/docs/employee) — full Employee class reference
- [Tools](/docs/tools) — built-in and custom tools
- [Integrations](/docs/integrations) — Gmail, Slack, GitHub, Stripe, and more
- [Evolution & Memory](/docs/sdk-evolution) — persistent learning

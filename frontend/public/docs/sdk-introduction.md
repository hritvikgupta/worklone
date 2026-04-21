# Worklone Employee SDK

The Worklone Employee SDK lets you create autonomous AI employees in Python. Each employee runs a full **ReAct loop** (Reason → Act → Observe), has access to 406 pre-built integration tools, learns from conversations over time, and can be wired into any multi-user SaaS product.

```bash
pip install worklone-employee
```

---

## What is an AI Employee?

An AI Employee is an autonomous agent that:

- **Reasons** about a task using an LLM
- **Acts** by calling tools (Gmail, Slack, GitHub, Stripe, custom functions)
- **Observes** tool results and decides what to do next
- **Learns** user preferences and successful task patterns over time

Unlike a simple chatbot, an Employee keeps working until the task is done — calling as many tools as it needs, in the right order, without you writing any orchestration logic.

---

## Quick Example

```python
from worklone_employee import Employee

emp = Employee(
    name="Aria",
    description="Executive assistant",
    model="anthropic/claude-sonnet-4-5",
    system_prompt="You are Aria, a sharp executive assistant. Always use tools before answering.",
    owner_id="user_123",
)

# Enable built-in tools
emp.use_tools(["web_search", "http_request"])

# Add a custom tool with a decorator
@emp.tool(description="Look up current price of a stock ticker")
def get_stock_price(ticker: str) -> str:
    prices = {"AAPL": "$189.30", "NVDA": "$875.00", "MSFT": "$415.50"}
    return prices.get(ticker.upper(), f"No data for {ticker}")

# Run a task
result = emp.run("What is NVIDIA's current stock price and recent news?")
print(result)
```

---

## Core Concepts

### ReAct Loop

Every employee runs a multi-step reasoning loop. You call `emp.run()` once — internally the agent calls tools, reads results, and iterates until it reaches a final answer.

```
User Message
    ↓
LLM Reasons → decides to call a tool
    ↓
Tool executes → returns result
    ↓
LLM Observes → decides: done or need more?
    ↓
Final Answer
```

### Tools

Tools are the actions an employee can take. The SDK ships with **406 pre-built tools** across 12 integrations (Gmail, Slack, Linear, GitHub, Stripe, etc.) plus system tools like web search, HTTP requests, and shell commands.

You can also register any Python function as a tool in one line using `@emp.tool`.

[→ Tooling Guide](/docs/sdk-tooling)

### Evolution

When `emp.enable_evolution()` is called, the employee learns over time:

- **Memory**: Extracts key facts from conversation history and stores them. On the next run, those memories are injected as context.
- **Skills**: Detects recurring tool usage patterns and saves them as reusable procedures.

[→ Evolution Guide](/docs/sdk-evolution)

### Integrations

OAuth-based integrations (Gmail, Slack, HubSpot, Jira, etc.) use a **TokenStore** pattern — your app stores tokens in its own database, the SDK reads through your store per user. No tokens are ever stored on Worklone's servers.

[→ Integrations Guide](/docs/integrations)

---

## Models

The SDK supports any LLM via [OpenRouter](https://openrouter.ai). Set your key once:

```python
import os
os.environ["OPENROUTER_API_KEY"] = "sk-or-..."
```

Then pass any model string:

```python
emp = Employee(model="anthropic/claude-sonnet-4-5")   # Claude
emp = Employee(model="openai/gpt-4o")                  # GPT-4o
emp = Employee(model="google/gemini-2.0-flash")        # Gemini
emp = Employee(model="meta-llama/llama-3.3-70b")       # Llama
```

---

## Installation

```bash
pip install worklone-employee
```

**Requirements:** Python 3.11+

**Dependencies:** `httpx`, `python-dotenv` (installed automatically)

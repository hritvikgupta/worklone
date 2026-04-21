# What is Worklone

Worklone is a Python SDK for building autonomous AI employees — agents that reason, use tools, and learn from interactions to complete real business tasks.

## The Problem

Most AI integrations today are wrappers. You call an LLM, it returns text, you parse it and do something. For anything beyond a simple Q&A, you end up writing orchestration logic: deciding which tool to call, when to stop, how to handle errors, how to pass context between steps.

Worklone eliminates that orchestration entirely.

## What an AI Employee Does

An AI Employee is an autonomous agent that:

1. **Receives** a plain-language task from your code or your user
2. **Reasons** about what steps are needed using an LLM
3. **Acts** by calling tools — Gmail, Slack, GitHub, custom functions, anything
4. **Observes** the results and decides what to do next
5. **Repeats** until the task is complete
6. **Returns** a final answer

You write one line: `emp.run("task")`. The employee handles the rest.

## The ReAct Loop

Under the hood every employee runs the ReAct pattern — **Re**ason + **Act**:

```
User Message
    ↓
LLM: "I need to search the web first"
    ↓
Tool: web_search("NVIDIA Q1 earnings")
    ↓
LLM: "Now I have data, I need stock price too"
    ↓
Tool: get_stock_price("NVDA")
    ↓
LLM: "I have everything, here is the summary"
    ↓
Final Answer → returned to your code
```

This loop runs automatically. No state machines, no prompt chaining, no manual routing.

## What Makes Worklone Different

### 406 Pre-Built Integration Tools

Gmail, Slack, Linear, GitHub, HubSpot, Jira, Stripe, Salesforce, Google Sheets, Google Calendar, Google Drive, Notion — all ready to use. No OAuth complexity in your agent code.

### Multi-Tenant by Design

One integration instance serves all your users. Tokens are stored in your own database — Worklone never stores credentials.

### Evolution & Memory

Employees learn from conversations. They extract facts, preferences, and successful task patterns — and apply them automatically in future sessions.

### Human-in-the-Loop

Built-in support for pausing and waiting for human approval before executing sensitive actions.

### Any LLM

Supports Claude, GPT-4o, Gemini, Llama, and 200+ models via OpenRouter. Switch models with one line.

## When to Use Worklone

Worklone is the right tool when your AI needs to **do things**, not just answer questions:

- Checking a user's Gmail and drafting replies
- Creating GitHub issues from a bug report
- Querying your database and generating a report
- Searching the web, synthesizing results, sending a Slack summary
- Running a multi-step sales workflow across HubSpot and email

If your use case is just generating text from a prompt, a raw LLM call is simpler. Worklone shines when the task requires tools, multiple steps, or persistent context.

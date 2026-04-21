# worklone-employee SDK — Comprehensive Build Plan

## What This Is

A **fully standalone, pip-installable Python SDK** for creating autonomous AI employees. No team runs, no workflow engine, no coworker messaging — just a single powerful employee with the full ReAct loop, managed tasks, evolution, and 250+ tool integrations.

```bash
pip install worklone-employee
```

```python
from worklone_employee import Employee

emp = Employee(
    name="Sales Bot",
    description="Handles all sales inquiries",
    model="anthropic/claude-sonnet-4-5",
    temperature=0.7,
    system_prompt="You are a sales assistant...",
    db="./my_project.db",   # optional — defaults to ~/.worklone/sdk.db
)

emp.use_tools(["gmail", "slack", "hubspot"])

@emp.tool(description="Look up product pricing")
def lookup_price(product_id: str) -> str:
    return f"Price for {product_id}: $99"

emp.enable_evolution()

response = emp.run("Send an email to john@example.com about our new product")

async for token in emp.stream("What deals closed this week?"):
    print(token, end="")
```

---

## Core Philosophy

1. **Zero imports from the backend** — completely self-contained package
2. **Core magic is untouched** — ReAct loop, managed background tasks, evolution (memory + skills) copied verbatim
3. **Only import paths change** — `from backend.X` becomes `from worklone_employee.X`, nothing else
4. **SQLite is hidden** — SDK manages the DB file transparently
5. **No team / workflow engine** — single employee only; team runs and workflow automation are backend-only features
6. **Publishable to PyPI** — proper `pyproject.toml`, versioned, installable

---

## What's Included vs Excluded

### Included (the employee magic)
- Full ReAct loop — reason → act → observe, no iteration limit, LLM decides when done
- Managed background tasks — `_run_background_task()` mini ReAct loop (max 20 cycles)
- Multi-step planning with user approval pause
- Memory evolution — background review every 8 turns, learns facts about the user
- Skill evolution — background review every 10 tool iterations, saves reusable procedures
- All 250+ integration tools (Gmail, Slack, HubSpot, GitHub, Notion, Linear, Stripe, Jira, etc.)
- All system tools (web search, web extract, file, shell, HTTP, memory, cronjob)
- All specialized tools (PM, engineer, analyst, designer, recruiter, sales, ops)
- Multi-provider LLM support (OpenRouter, NVIDIA, OpenAI, Groq)
- Native streaming with function calling

### Excluded (backend-only features)
- Team runs / multi-employee orchestration → `team_store.py` not needed
- Inter-employee coworker messaging → `_await_coworker_reply()` removed from react_agent
- Workflow automation engine → `workflow_store.py` not needed
- Team context / team memory tools → not included
- Coworker tools → not included

---

## Session & Database

The existing agent uses SQLite. We keep it — we just hide it.

- `APP_DB` env var is set by the SDK before any store is instantiated (this is how `database.py` already works)
- Default path: `~/.worklone/sdk.db` — created automatically
- User can override: `Employee(db="./my_project.db")`
- Employee is identified by a deterministic ID from `name + owner_id` — re-creating `Employee(name="Sales Bot")` reuses the same DB row, no duplicates
- Message history is in-memory within a Python session (on the agent instance)
- Evolution data (memory, skills) persists across sessions in SQLite automatically
- `emp.reset()` clears message history for a fresh conversation; keeps employee config and evolution data

---

## Actual Dependency Map (Traced — Only What's Needed)

```
react_agent.py  (stripped of team/coworker code)
├── providers/config.py          (llm_config — simplified, no WorkflowStore)
├── db/store.py                  (EmployeeStore — employees, tools, skills, tasks, activity)
│   ├── db/database.py
│   ├── types.py
│   ├── workflows/utils.py       (generate_id, now_iso)
│   └── logging/logger.py
├── types.py                     (Employee, EmployeeTool, EmployeeSkill, etc.)
├── tools/catalog.py             (create_tool factory, DEFAULT_EMPLOYEE_TOOL_NAMES)
│   ├── tools/base.py
│   ├── tools/system/*
│   ├── tools/employee/*         (ask_user, run_task, task, send_message, check_messages, document)
│   ├── tools/specialized/*
│   ├── tools/workflow/*         (approval only — monitoring optional)
│   ├── tools/run/*
│   ├── tools/data/*
│   └── tools/integrations/**   (250+ files)
├── tools/registry.py
│   ├── tools/base.py
│   └── logging/logger.py
├── tools/employee/ask_user_tool.py
├── tools/employee/run_task_tool.py
├── tools/employee/send_message_tool.py   (kept — defines AWAIT_COWORKER_MARKER constant only)
├── logging/logger.py
├── workflows/utils.py
├── evolution/evolution_store.py
│   ├── db/database.py
│   ├── workflows/utils.py
│   └── logging/logger.py
└── evolution/background_review.py
    ├── evolution/evolution_store.py
    ├── providers/config.py
    └── logging/logger.py
```

**Not needed:** `workflow_store.py`, `team_store.py`, `workflows/types.py`, `workflows/schedules.py`

---

## Complete Package Structure

```
worklone-employee/                          ← SDK root (in repo root)
│
├── pyproject.toml
├── README.md
│
└── worklone_employee/
    │
    ├── __init__.py                         ← exports: Employee, BaseTool, ToolResult
    ├── employee.py                         ← Employee() class — NEW FILE
    │
    ├── agents/
    │   ├── __init__.py
    │   └── react_agent.py                  ← FULL COPY of backend react_agent.py
    │                                          REMOVE: team_id/run_id params, _await_coworker_reply(),
    │                                                  AWAIT_COWORKER handling block,
    │                                                  team tools registration block (lines 474-491)
    │                                          CHANGE: import paths only for everything else
    │
    ├── evolution/
    │   ├── __init__.py
    │   ├── evolution_store.py              ← FULL COPY — no changes except import paths
    │   └── background_review.py            ← FULL COPY — no changes except import paths
    │
    ├── tools/
    │   ├── __init__.py
    │   ├── base.py                         ← FULL COPY — zero changes
    │   ├── registry.py                     ← FULL COPY — import paths only
    │   ├── catalog.py                      ← FULL COPY — import paths only
    │   │                                      (remove team_context_tool and team_memory_tool entries)
    │   │
    │   ├── system/                         ← FULL COPY of system_tools/
    │   │   ├── web_search_tool.py
    │   │   ├── web_extract_tool.py
    │   │   ├── file_tool.py
    │   │   ├── http_tool.py
    │   │   ├── shell_tool.py
    │   │   ├── memory_tool.py
    │   │   ├── session_search_tool.py
    │   │   └── cronjob_tool.py
    │   │
    │   ├── employee/                       ← FULL COPY of employee_tools/
    │   │   ├── ask_user_tool.py            (keep — human pause in ReAct loop)
    │   │   ├── run_task_tool.py            (keep — managed background tasks)
    │   │   ├── task_tool.py                (keep — task CRUD)
    │   │   ├── send_message_tool.py        (keep — defines AWAIT_COWORKER_MARKER constant)
    │   │   ├── check_messages_tool.py      (keep)
    │   │   └── document_tools.py           (keep)
    │   │   NOTE: team_context_tool.py and team_memory_tool.py → NOT included
    │   │
    │   ├── specialized/                    ← FULL COPY — import paths only
    │   │   ├── pm_tools.py
    │   │   ├── engineer_tools.py
    │   │   ├── analyst_tools.py
    │   │   ├── designer_tools.py
    │   │   ├── recruiter_tools.py
    │   │   ├── sales_tools.py
    │   │   └── ops_tools.py
    │   │
    │   ├── workflow/                       ← PARTIAL — only approval_tool
    │   │   ├── approval_tool.py            (keep — used by plan approval flow)
    │   │   NOTE: coworker_tools.py, monitoring_tools.py → NOT included
    │   │
    │   ├── run/                            ← FULL COPY — import paths only
    │   │   ├── function_tool.py
    │   │   └── llm_tool.py
    │   │
    │   ├── data/                           ← FULL COPY — import paths only
    │   │   └── sql_tool.py
    │   │
    │   └── integrations/                   ← FULL COPY of integration_tools_v2/
    │       ├── gmail/
    │       ├── slack/
    │       ├── hubspot/
    │       ├── notion/
    │       ├── github/
    │       ├── linear/
    │       ├── salesforce/
    │       ├── stripe/
    │       ├── jira/
    │       ├── google_drive/
    │       ├── google_calendar/
    │       ├── hunter/
    │       ├── attio/
    │       ├── agentmail/
    │       └── dspy/
    │
    ├── providers/
    │   ├── __init__.py
    │   ├── base.py                         ← LLMProvider ABC — import paths only
    │   ├── openrouter.py                   ← OpenRouterProvider — import paths only
    │   ├── nvidia.py                       ← NVIDIAProvider — import paths only
    │   ├── openai.py                       ← OpenAIProvider — import paths only
    │   ├── groq.py                         ← GroqProvider — import paths only
    │   ├── factory.py                      ← LLMProviderFactory — import paths only
    │   └── config.py                       ← COPY of llm_config.py
    │                                          CHANGE: remove get_user_provider_config() WorkflowStore
    │                                          dependency — replace with env var lookup only
    │                                          (user passes API keys via env: OPENROUTER_API_KEY etc.)
    │
    ├── db/
    │   ├── __init__.py
    │   ├── database.py                     ← FULL COPY — zero changes (pure stdlib)
    │   └── store.py                        ← FULL COPY of employee_store.py — import paths only
    │                                          NOTE: team_store.py NOT included
    │
    ├── workflows/
    │   ├── __init__.py
    │   └── utils.py                        ← FULL COPY of workflows/utils.py — zero changes
    │                                          (generate_id, now_iso, resolve_template, etc.)
    │                                          NOTE: workflows/types.py and schedules NOT needed
    │
    └── logging/
        ├── __init__.py
        └── logger.py                       ← FULL COPY — zero changes
```

---

## File-by-File Action Table

| SDK File | Source | Action | What Changes |
|---|---|---|---|
| `agents/react_agent.py` | `backend/core/agents/employee/react_agent.py` | Copy + strip | Remove `team_id`/`run_id`, `_await_coworker_reply()`, AWAIT_COWORKER block, team tools registration. Update import paths. |
| `evolution/evolution_store.py` | `backend/core/agents/evolution/evolution_store.py` | Full copy | Import paths only |
| `evolution/background_review.py` | `backend/core/agents/evolution/background_review.py` | Full copy | Import paths only |
| `tools/base.py` | `backend/core/tools/system_tools/base.py` | Full copy | Nothing |
| `tools/registry.py` | `backend/core/tools/system_tools/registry.py` | Full copy | Import paths only |
| `tools/catalog.py` | `backend/core/tools/catalog.py` | Copy + strip | Remove team_context_tool and team_memory_tool entries. Update import paths. |
| `tools/system/*` | `backend/core/tools/system_tools/*` | Full copy | Import paths only |
| `tools/employee/*` | `backend/core/tools/employee_tools/*` | Partial copy | Exclude team_context_tool.py and team_memory_tool.py |
| `tools/specialized/*` | `backend/core/tools/specialized_tools/*` | Full copy | Import paths only |
| `tools/workflow/approval_tool.py` | `backend/core/tools/workflow_tools/approval_tool.py` | Full copy | Import paths only |
| `tools/run/*` | `backend/core/tools/run_tools/*` | Full copy | Import paths only |
| `tools/data/*` | `backend/core/tools/data_tools/*` | Full copy | Import paths only |
| `tools/integrations/*` | `backend/core/tools/integration_tools_v2/*` | Full copy | Import paths only |
| `providers/config.py` | `backend/services/llm_config.py` | Copy + simplify | Remove WorkflowStore import in `get_user_provider_config()` — replace with env var lookup |
| `providers/base.py` | `backend/services/llm_provider.py` | Extract LLMProvider ABC | Import paths only |
| `providers/openrouter.py` | `backend/services/llm_provider.py` | Extract OpenRouterProvider | Import paths only |
| `providers/nvidia.py` | `backend/services/llm_provider.py` | Extract NVIDIAProvider | Import paths only |
| `providers/openai.py` | `backend/services/llm_provider.py` | Extract OpenAIProvider | Import paths only |
| `providers/groq.py` | `backend/services/llm_provider.py` | Extract GroqProvider | Import paths only |
| `providers/factory.py` | `backend/services/llm_provider.py` | Extract LLMProviderFactory | Import paths only |
| `db/database.py` | `backend/db/database.py` | Full copy | Nothing |
| `db/store.py` | `backend/db/stores/employee_store.py` | Full copy | Import paths only |
| `workflows/utils.py` | `backend/core/workflows/utils.py` | Full copy | Nothing |
| `logging/logger.py` | `backend/core/logging/logger.py` | Full copy | Nothing |
| `types.py` | `backend/core/agents/employee/types.py` | Full copy | Nothing (team types are harmless dataclasses) |
| `employee.py` | — | **New file** | Full SDK entry point |
| `__init__.py` | — | **New file** | Public surface |

---

## The `employee.py` — New SDK Entry Point

### Constructor

```python
Employee(
    name: str,
    description: str = "",
    model: str = "openai/gpt-4o",
    temperature: float = 0.7,
    system_prompt: str = "",
    db: str | None = None,          # defaults to ~/.worklone/sdk.db
    owner_id: str = "sdk_user",
)
```

**Init flow:**
1. Resolve DB path → set `os.environ["APP_DB"]` → create `~/.worklone/` dir if needed
2. Import and instantiate `EmployeeStore` (deferred import — after APP_DB is set)
3. Generate deterministic `employee_id = "sdk_" + md5(f"{owner_id}:{name}")[:12]`
4. If row exists → update model/temp/system_prompt/description
5. If row doesn't exist → `store.create_employee(...)` with all config
6. Set `_pending_custom_tools = []`, `_agent = None` (lazy), `_evolution_enabled = False`

### Methods

| Method | What it does |
|---|---|
| `use_tools(names: list[str])` | Writes `EmployeeTool` rows to DB. Agent picks them up via `_register_tools()` on build. Guards against duplicates. |
| `@emp.tool(description)` | Wraps a plain Python function as a `BaseTool` subclass. Added to `_pending_custom_tools`. |
| `add_tool(instance: BaseTool)` | Adds a pre-built `BaseTool` instance. Added to `_pending_custom_tools`. |
| `enable_evolution()` | Sets `_evolution_enabled = True`. Agent built with counters at 0 so reviews fire normally. |
| `_ensure_agent()` | Lazy-builds `GenericEmployeeAgent`. Injects `_pending_custom_tools` into registry after build. |
| `run(message: str) -> str` | Sync. `asyncio.run()` wrapper. Returns final answer string. |
| `stream(message: str)` | Async generator. Yields tokens from `agent.chat()`. |
| `reset()` | Clears `agent.messages`. Keeps DB row and evolution data. |

### FunctionToolAdapter (inside `employee.py`)

Converts a plain function to `BaseTool`:
- `get_schema()` → introspects `inspect.signature(fn)` → builds JSON Schema from type annotations
- `execute(parameters, context)` → calls `fn(**parameters)` → wraps in `ToolResult`

---

## `providers/config.py` — The One Real Logic Change

`get_user_provider_config()` in the original `llm_config.py` does this:

```python
# Original — imports WorkflowStore to look up per-user API keys from DB
from backend.db.stores.workflow_store import WorkflowStore
store = WorkflowStore()
creds = store.get_user_credentials(owner_id, provider_name)
```

In the SDK this becomes:

```python
# SDK — reads from environment variables only
api_key = os.getenv(f"{provider_name.upper()}_API_KEY") or os.getenv("OPENROUTER_API_KEY")
```

Users set their API keys via env vars or `.env` file. No DB lookup needed.
This is the **only logic change** in the entire SDK — everything else is copy + import path update.

---

## `__init__.py` — Public Surface

```python
from worklone_employee.employee import Employee
from worklone_employee.tools.base import BaseTool, ToolResult

__all__ = ["Employee", "BaseTool", "ToolResult"]
```

---

## `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "worklone-employee"
version = "0.1.0"
description = "Autonomous AI employees with ReAct loop, evolution, and 250+ integrations"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["worklone_employee*"]
```

---

## Build Order

### Step 1 — Foundation (no deps)
- `worklone_employee/types.py`
- `worklone_employee/logging/logger.py`
- `worklone_employee/db/database.py`
- `worklone_employee/workflows/utils.py`

### Step 2 — Store
- `worklone_employee/db/store.py` (EmployeeStore)

### Step 3 — Providers
- `worklone_employee/providers/base.py`
- `worklone_employee/providers/config.py` (simplified llm_config)
- `worklone_employee/providers/openrouter.py`
- `worklone_employee/providers/nvidia.py`
- `worklone_employee/providers/openai.py`
- `worklone_employee/providers/groq.py`
- `worklone_employee/providers/factory.py`

### Step 4 — Tool Framework
- `worklone_employee/tools/base.py`
- `worklone_employee/tools/registry.py`

### Step 5 — All Tools (bulk copy + import path update)
- `worklone_employee/tools/system/*`
- `worklone_employee/tools/employee/*` (skip team_context, team_memory)
- `worklone_employee/tools/specialized/*`
- `worklone_employee/tools/workflow/approval_tool.py`
- `worklone_employee/tools/run/*`
- `worklone_employee/tools/data/*`
- `worklone_employee/tools/integrations/**`
- `worklone_employee/tools/catalog.py`

### Step 6 — Evolution
- `worklone_employee/evolution/evolution_store.py`
- `worklone_employee/evolution/background_review.py`

### Step 7 — Core Agent
- `worklone_employee/agents/react_agent.py`
  Copy full file. Strip team/coworker sections. Update all import paths.

### Step 8 — SDK Entry Point
- `worklone_employee/employee.py` (new)
- `worklone_employee/__init__.py` (new)

### Step 9 — Package Config
- `pyproject.toml`
- `worklone_employee/py.typed`

### Step 10 — Smoke Test
```python
# test_sdk.py (run from repo root after: pip install -e worklone-employee/)
from worklone_employee import Employee

emp = Employee(name="Test", model="openai/gpt-4o", db="/tmp/sdk_test.db")
emp.use_tools(["web_search"])
print(emp.run("What is 2 + 2?"))
```

---

## Guaranteed to Work Identically

| Feature | Status |
|---|---|
| ReAct loop (reason → act → observe, LLM-controlled) | Identical |
| Managed background tasks (`_run_background_task`, max 20 cycles) | Identical |
| Multi-step planning with approval pause | Identical |
| Memory evolution (background review every 8 turns) | Identical |
| Skill evolution (background review every 10 tool iters) | Identical |
| All 250+ integration tools | Identical |
| All system / specialized / run / data tools | Identical |
| Native LLM function calling with streaming | Identical |
| Multi-provider support (OpenRouter, NVIDIA, OpenAI, Groq) | Identical |
| Cost estimation per model | Identical |
| Human-in-the-loop (`ask_user` pause/resume) | Identical |

---

## What's Different From the Backend

| Aspect | Backend | SDK |
|---|---|---|
| DB path | `workflows.db` in repo root | `~/.worklone/sdk.db` or user-specified |
| Employee creation | REST API + frontend | `Employee()` constructor |
| Tool assignment | Frontend UI | `emp.use_tools()` |
| Per-user API keys | Stored in WorkflowStore DB | Env vars / `.env` file |
| Streaming output | WebSocket → frontend | `async for token in emp.stream()` |
| Evolution | Always on | Opt-in via `emp.enable_evolution()` |
| Custom tools | Not supported | `@emp.tool()` and `emp.add_tool()` |
| Team runs | Supported | Not included |
| Inter-employee messaging | Supported | Not included |

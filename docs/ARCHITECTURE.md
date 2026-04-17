# Architecture Overview

Worklone is a full-stack platform for deploying AI employees that reason, act, and learn. This document explains how the system is designed, how components interact, and the principles that guide the architecture.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Worklone Platform                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    FRONTEND (React 19)                       │   │
│  │                                                              │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐     │   │
│  │  │ Dashboard  │  │ Chat UI    │  │ Workflow Builder   │     │   │
│  │  │ & Analytics│  │ (SSE + WS) │  │ (Drag & Drop)      │     │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘     │   │
│  │                                                              │   │
│  │  Tech: TypeScript · Vite · Tailwind CSS v4 · shadcn/ui      │   │
│  │        · Recharts · React Router · Framer Motion            │   │
│  └──────────────────────────┬───────────────────────────────────┘   │
│                             │ HTTP / SSE / WebSocket                │
│  ┌──────────────────────────▼───────────────────────────────────┐   │
│  │                    BACKEND (FastAPI)                         │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │                  API Layer (routers/)                 │   │   │
│  │  │  Auth · Chat · Employees · Workflows · Teams         │   │   │
│  │  │  Sprints · Dashboard · Files · Skills · OAuth        │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                             │                                │   │
│  │  ┌──────────────────────────▼───────────────────────────┐   │   │
│  │  │               Service Layer (services/)               │   │   │
│  │  │  KatyService · EmployeeService · LLMProvider         │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                             │                                │   │
│  │  ┌──────────────────────────▼───────────────────────────┐   │   │
│  │  │              Core Engine (core/)                      │   │   │
│  │  │                                                       │   │   │
│  │  │  ┌────────────┐  ┌────────────┐  ┌───────────────┐  │   │   │
│  │  │  │ Agents     │  │ Tools      │  │ Workflows     │  │   │   │
│  │  │  │ (ReAct)    │  │ (500+)     │  │ (DAG Engine)  │  │   │   │
│  │  │  └────────────┘  └────────────┘  └───────────────┘  │   │   │
│  │  │                                                       │   │   │
│  │  │  ┌───────────────────────────────────────────────┐   │   │   │
│  │  │  │         Self-Learning System                  │   │   │   │
│  │  │  │  User Memory · Learned Skills · Evolution     │   │   │   │
│  │  │  └───────────────────────────────────────────────┘   │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                             │                                │   │
│  │  ┌──────────────────────────▼───────────────────────────┐   │   │
│  │  │           Data Layer (db/stores/)                     │   │   │
│  │  │  AuthStore · EmployeeStore · WorkflowStore           │   │   │
│  │  │  TeamStore · SprintStore · FileStore                 │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  PERSISTENCE (SQLite)                        │   │
│  │  employees · workflows · skills · memory · auth · files     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Agent Engine (`backend/core/agents/`)

The agent engine implements the **ReAct (Reasoning + Acting)** pattern using native LLM function calling.

#### How It Works

```
User Message
    │
    ▼
┌─────────────────┐
│ Build Context   │ ← System prompt + tools + memory + learned skills
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Call       │ ← Streaming response with function calling
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
Content   Tool Calls
 (done)       │
              ▼
     ┌─────────────────┐
     │ Execute Tools   │ ← Run tool, get result
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │ Append Result   │ ← Add as role: "tool" message
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │  Loop to LLM    │ ← LLM decides: more tools or final answer
     └─────────────────┘
```

**Key design principles:**
- **No iteration limits** — the LLM decides when it's done
- **No keyword matching** — pure function calling, no regex parsing
- **Streaming support** — real-time token output via SSE/WebSocket
- **Mandatory planning** — multi-step requests require a plan before execution

#### Agent Types

| Agent | Description | Location |
|-------|-------------|----------|
| **Katy** | Pre-built AI Product Manager with PM-specific tools and expertise | `core/agents/product_manager/` |
| **Generic Employee** | Configurable agent loaded from database with custom role, tools, and skills | `core/agents/employee/` |
| **Evolution System** | Background learner that reviews conversations and extracts memory/skills | `core/agents/evolution/` |

---

### 2. Tool System (`backend/core/tools/`)

Every tool implements the `BaseTool` abstract class:

```python
class BaseTool(ABC):
    name: str
    description: str
    
    @abstractmethod
    def get_schema(self) -> dict:
        """Return OpenAI function-calling schema"""
    
    @abstractmethod
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        """Execute the tool with given parameters"""
```

Tools are organized into categories:

| Category | Description | Examples |
|----------|-------------|----------|
| **System Tools** | Core utilities | File I/O, HTTP requests, shell commands, memory |
| **Integration Tools** | External services | GitHub, Slack, Gmail, Jira, Notion, Salesforce, Stripe |
| **Employee Tools** | Agent collaboration | Task management, messaging coworkers, async tasks |
| **Workflow Tools** | Workflow management | Create workflows, add blocks, execute, monitor |
| **Specialized Tools** | Role-specific | PM tools, engineer tools, analyst tools, sales tools |
| **Run Tools** | LLM & execution | LLM calls, function execution |
| **Data Tools** | Data operations | SQL queries, data analysis |

The `ToolRegistry` manages all tools, converts them to OpenAI function-calling format, and handles execution with credential injection.

---

### 3. Workflow Engine (`backend/core/workflows/`)

A DAG-based execution engine that supports complex workflow patterns.

#### Block Types

| Block | Purpose |
|-------|---------|
| `start` | Entry point, receives input data |
| `agent` | Invokes an AI employee |
| `tool` | Executes a single tool |
| `function` | Runs custom Python code |
| `http` | Makes HTTP requests |
| `condition` | Branching logic (if/else) |
| `loop` | Iteration over collections |
| `parallel` | Concurrent execution |
| `wait` | Timed delays |
| `variable` | Data manipulation |
| `trigger` | External event triggers |
| `human_approval` | Human-in-the-loop pause |
| `end` | Workflow completion |

#### Trigger Types

| Trigger | Description |
|---------|-------------|
| `api` | Manual API call |
| `webhook` | External webhook |
| `schedule` | Cron-based scheduling |
| `manual` | UI-triggered |

#### Execution Flow

```
Trigger → Job Queue → DAG Builder → Topological Sort → Execute Blocks → Store Results
```

The background worker (`worker.py`) polls for scheduled workflows every 5 seconds and executes them with configurable concurrency limits.

---

### 4. Self-Learning System (`backend/core/agents/evolution/`)

The evolution system makes Worklone employees **adaptive** — they learn and improve over time without manual intervention.

#### User Memory

- **What**: Declarative facts about users (preferences, work style, goals, communication patterns)
- **When**: Every 8 conversation turns
- **How**: LLM reviews the conversation and merges new facts into existing memory
- **Storage**: `employee_user_memory` table in SQLite

#### Learned Skills

- **What**: Procedural knowledge — multi-step procedures discovered through trial-and-error
- **When**: Every 10 tool iterations
- **How**: LLM identifies non-trivial procedures and writes them as markdown skill documents
- **Storage**: `employee_learned_skills` table with versioning
- **Usage**: Injected into system prompt for future conversations

#### Background Processing

Reviews run in a `ThreadPoolExecutor` (max 2 workers) — fire-and-forget, never blocking the main chat loop.

---

### 5. API Layer (`backend/api/`)

FastAPI-based REST API with 10 routers:

| Router | Base Path | Purpose |
|--------|-----------|---------|
| `auth_router` | `/api/auth` | Registration, login, sessions, API keys |
| `chat_router` | `/api/chat` | Katy chat (streaming + non-streaming) |
| `employee_router` | `/api/employees` | Employee CRUD, tools, skills, tasks |
| `workflow_router` | `/api/workflows` | Workflow CRUD, blocks, execution |
| `team_router` | `/api/teams` | Team management, team runs |
| `sprint_router` | `/api/sprints` | Sprint management, task runs |
| `dashboard_router` | `/api/dashboard` | Usage statistics, overview |
| `file_router` | `/api/files` | File upload, download, tree |
| `skills_router` | `/api/skills` | Public skills library, generation |
| `oauth_router` | `/api/oauth` | OAuth connect/disconnect |

Authentication supports API keys, user ID headers, and bearer tokens.

---

### 6. Data Layer (`backend/db/`)

All data is stored in a single SQLite file (`workflows.db` by default).

| Store | Tables | Purpose |
|-------|--------|---------|
| `AuthStore` | users, sessions, api_keys | Authentication and authorization |
| `EmployeeStore` | employees, tools, skills, tasks, memory | Employee management and learning |
| `WorkflowStore` | workflows, blocks, executions | Workflow definitions and history |
| `TeamStore` | teams, team_runs | Team collaboration |
| `SprintStore` | sprints, sprint_runs | Sprint execution |
| `FileStore` | files | File storage |

**Data isolation**: Every record is scoped to `owner_id` for multi-tenant safety.

---

## Data Flow

### Chat Flow

```
User → Frontend → API → Service → Agent → LLM → (Tools) → Response → Frontend → User
                              │
                              ▼
                         Evolution System
                         (background review)
```

### Workflow Flow

```
Trigger → Worker → DAG Builder → Block Handlers → Results → Notification
```

### Learning Flow

```
Conversation → Background Thread → LLM Review → Memory/Skills → Next Conversation
```

---

## Design Principles

1. **Zero-config persistence** — SQLite, no Redis or PostgreSQL required
2. **Autonomous agents** — LLM decides everything via function calling, no hardcoded logic
3. **Extensible tools** — add a new tool in under 50 lines of code
4. **Self-improving** — employees learn from every interaction
5. **Self-hosted** — your data never leaves your infrastructure
6. **Developer-first** — clean APIs, readable code, comprehensive docs

---

## Deployment

Worklone is designed for self-hosting:

- **Development**: `./start.sh` for local development
- **Production**: Run with `uvicorn` behind a reverse proxy (nginx/caddy)
- **Docker**: Coming soon

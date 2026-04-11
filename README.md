# Workflow Engine — AI Co-Worker Platform

Complete workflow automation system. No Sim dependency. No licensing fees. 100% yours.

## Project Structure

```
ceo-agent/
├── backend/                    ← FastAPI server (your main entry point)
│   ├── main.py                 ← All 32 API endpoints + startup/shutdown
│   ├── core/
│   │   ├── config.py           ← Environment settings
│   │   └── dependencies.py     ← Shared service instances
│   ├── services/
│   │   ├── auth_service.py     ← Users + API keys
│   │   └── workflow_service.py ← Workflow/Block/Edge/Trigger CRUD
│   └── api/
│       ├── auth_middleware.py  ← Auth extraction
│       └── auth_router.py      ← Auth endpoints (supplemental)
│
├── workflows/                  ← Core engine (27 files)
│   ├── types.py                ← Data models
│   ├── store.py                ← Multi-tenant SQLite persistence
│   ├── utils.py                ← Template resolver, ID gen
│   ├── logger.py               ← Logging
│   ├── coworker.py             ← ReAct co-worker agent
│   ├── coworker_tools.py       ← Workflow management tools
│   ├── worker.py               ← Background job processor + scheduler
│   ├── tools/                  ← Integration tools (HTTP, LLM, Slack, Gmail, etc.)
│   └── engine/                 ← DAG execution engine
│       ├── dag_builder.py      ← Workflow → DAG
│       ├── executor.py         ← Parallel-aware executor
│       ├── variable_resolver.py← {{block.output}} resolution
│       └── handlers/           ← Block type handlers
│
├── scripts/                    ← Test scripts
├── .reference/                 ← Old Sim code (for reference only)
├── agent-harness/              ← Frontend (connects to backend)
├── .env.example                ← Environment template
└── requirements.txt
```

## Quick Start

```bash
# 1. Setup
cp .env.example .env
# Edit .env — add OPENROUTER_API_KEY

# 2. Run server
uvicorn backend.main:app --reload --port 8002

# 3. Test
curl http://localhost:8002/health
```

## API Endpoints (32 total)

### Auth
```
POST   /api/auth/register          {"user_id": "user-1", "name": "Alice"}
GET    /api/users/me               (header: x-user-id: user-1)
POST   /api/auth/keys              Create API key (raw key shown once)
GET    /api/auth/keys              List keys
DELETE /api/auth/keys/{id}         Revoke key
```

### Workflows
```
GET    /api/workflows              List (filtered by user)
POST   /api/workflows              Create
GET    /api/workflows/{id}         Full details (blocks + edges + triggers)
PATCH  /api/workflows/{id}         Update metadata
DELETE /api/workflows/{id}         Delete
```

### Blocks
```
POST   /api/workflows/{id}/blocks       Add block
PATCH  /api/workflows/blocks/{id}       Update block
DELETE /api/workflows/blocks/{id}       Delete block
```

### Edges
```
POST   /api/workflows/{id}/edges        Add edge
DELETE /api/workflows/edges/{id}        Delete edge
```

### Triggers
```
POST   /api/workflows/{id}/triggers     Add trigger (webhook/schedule/api/manual)
PATCH  /api/workflows/triggers/{id}     Update (enable/disable)
DELETE /api/workflows/triggers/{id}     Delete
```

### Execution
```
POST   /api/workflows/{id}/execute      Run (sync or async)
GET    /api/workflows/{id}/executions   History
```

### Webhooks (catch-all)
```
POST   /api/webhooks/{path}             Receive webhook → queue execution
```

### Schedules
```
GET    /api/schedules                   List schedules
POST   /api/schedules/tick              Trigger dispatch (for external cron)
```

### Other
```
GET    /api/jobs                        Background jobs
GET    /api/tools                       Available tools
POST   /api/coworker/chat               Talk to AI co-worker
GET    /health                          Health check
GET    /                                API info
```

## Connecting from agent-harness Frontend

```javascript
// In agent-harness, make requests with:
const BASE = 'http://localhost:8002';
const HEADERS = { 'x-user-id': 'your-user-id' };

// Create workflow
const wf = await fetch(`${BASE}/api/workflows`, {
  method: 'POST',
  headers: { ...HEADERS, 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'my-workflow', description: '...' }),
});

// Add block
await fetch(`${BASE}/api/workflows/${wf.id}/blocks`, {
  method: 'POST',
  headers: { ...HEADERS, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    block_type: 'agent',
    name: 'Analyze',
    model: 'openai/gpt-4o',
    system_prompt: 'You are...',
    prompt: 'Analyze this data...',
  }),
});

// Add edge
await fetch(`${BASE}/api/workflows/${wf.id}/edges`, {
  method: 'POST',
  headers: { ...HEADERS, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    from_block_id: 'blk_abc',
    to_block_id: 'blk_xyz',
  }),
});

// Execute
const result = await fetch(`${BASE}/api/workflows/${wf.id}/execute`, {
  method: 'POST',
  headers: { ...HEADERS, 'Content-Type': 'application/json' },
  body: JSON.stringify({ input_data: { key: 'value' } }),
});
```

## How It Works

### Triggers (like Sim's)
- **Webhook**: POST to `/api/webhooks/{path}` → finds trigger → queues job → executes workflow
- **Schedule**: ScheduleDispatcher polls for due schedules → enqueues → worker executes
- **API**: POST `/api/workflows/{id}/execute`
- **Manual**: Same as API, tracked separately

### Parallel Execution (like Sim's)
- Sentinel nodes injected during graph building
- Branch cloning with `₍n₎` subscript notation
- Topological sort respects all DAG dependencies
- Result aggregation at end sentinel

### Background Worker
- Polls every 5s for pending jobs
- Retry with exponential backoff (max 3 attempts)
- Job types: `workflow_execution`, `schedule_dispatch`
- SQLite-based queue (no Redis)

### Multi-Tenant
- Every record scoped to `owner_id`
- Users auto-created on first access
- API keys: `wf_<random>`, SHA-256 hashed
- Three auth methods: API key, Bearer token, x-user-id header

## Environment Variables

```
OPENROUTER_API_KEY=sk-or-...     # Required for LLM
SLACK_BOT_TOKEN=xoxb-...         # Optional
GMAIL_ACCESS_TOKEN=ya29....      # Optional
WORKFLOW_DB=workflows.db          # SQLite path
PORT=8002                         # Server port
```

# ceo-agent: Production Parallelization Plan

Blueprint to run **many employees, teams, sprints, and workflows in parallel** across many users, with queues, backpressure, cancellation, and race-safe identity — modeled on Sim's architecture (`.reference/sim/`) and adapted for our Python/FastAPI backend.

---

## 1. Current state (what exists today)

| Area | File | Problem at scale |
|---|---|---|
| Employee ReAct loop | `backend/core/agents/employee/react_agent.py` (1417 loc) | Runs in-process in the API request — one slow LLM call blocks a uvicorn worker |
| Team runner | `backend/core/agents/employee/team_runner.py` (498 loc) | Fans out via `asyncio.gather` inside one request; no cross-process parallelism |
| Sprint runner | `backend/core/agents/employee/sprint_runner.py` (333 loc) | Same as team — single-process |
| Workflow engine | `backend/core/workflows/engine/coworker.py` (Harry — ReAct over a sequential task list), `executor.py` | Runs inline in the API request |
| Workflow worker | `backend/core/workflows/worker.py` | Polling loop in a single asyncio task — single point of failure |
| Persistence | `backend/db/stores/*_store.py` | SQLite (`workflows.db`) — blocks under concurrent writers |
| Identity | `employee_id`, `team_id` everywhere | No per-run IDs → race conditions when same entity runs twice |

**The core issue:** everything runs in the API process, state is keyed by entity ID (not run ID), and there's no queue — so two concurrent invocations of the same employee race on shared state, logs interleave, and cancellation is ambiguous.

### Important: we are NOT Sim

Sim executes a **DAG** of blocks — they parallelize *inside* a single workflow by expanding parallel nodes. **We don't have a DAG.** Our building blocks are all **ReAct agents executing sequentially within one run**:

- **Employee** (`react_agent.py`) — ReAct loop over tools, one step at a time.
- **Harry / coworker** (`coworker.py`) — ReAct loop over a **list of tasks**, one task at a time. Sequential by design (Task N may depend on Task N-1's output).
- **Team** (`team_runner.py`) — coordinates multiple employees.
- **Sprint** (`sprint_runner.py`) — coordinates a team toward a goal.

So our parallelism story is **different from Sim's**:

> We parallelize at the **run level**, not the **step level**. Inside one `workflow_run`, Harry still does task 1 → task 2 → task 3 sequentially. Across many `workflow_run`s, thousands execute concurrently on different workers.

Where we DO fan out: teams and sprints, where multiple **employees** run in parallel as independent jobs (each itself sequential internally).

This is why the queue/worker architecture matters more than any internal DAG engine — horizontal parallelism comes from running many runs side-by-side, not from splitting one run into parallel steps.

---

## 2. Target architecture — 3 layers

```
┌──────────────────────────────────────────────────────────┐
│  LAYER 1 — API (FastAPI)                                 │
│  backend/api/                                            │
│  - admission gate (per-pod semaphore, 429 at capacity)   │
│  - validates → enqueues → returns execution_id           │
│  - NEVER executes agent/workflow code                    │
└─────────────────────┬────────────────────────────────────┘
                      │ enqueue
┌─────────────────────▼────────────────────────────────────┐
│  LAYER 2 — Dispatcher (Redis)                            │
│  backend/core/dispatch/                                  │
│  - per-user lanes (fairness)                             │
│  - per-user queue depth cap (1000)                       │
│  - global queue depth cap (50000)                        │
│  - round-robin pull → arq named queues                   │
└─────────────────────┬────────────────────────────────────┘
                      │ dispatch
┌─────────────────────▼────────────────────────────────────┐
│  LAYER 3 — Workers (arq on Redis)                        │
│  backend/workers/                                        │
│  - one process family per queue (employee, team, ...)    │
│  - each sets its own concurrency & retry policy          │
│  - scale horizontally via docker-compose replicas        │
└──────────────────────────────────────────────────────────┘
```

**Choice: arq over Celery.** Agent code is async-heavy (LLM streaming, HTTP, DB). arq is asyncio-native and pairs cleanly with FastAPI. Celery is acceptable if the team prefers it — the architecture is identical.

---

## 3. Queue topology

| Queue | Handler | Concurrency | Retries | Backoff |
|---|---|---|---|---|
| `employee-run` | `backend/workers/employee.py::run_employee` | 50 | 3 | exp 1s |
| `team-run` | `backend/workers/team.py::run_team` | 20 | 2 | exp 2s |
| `sprint-run` | `backend/workers/sprint.py::run_sprint` | 10 | 2 | exp 2s |
| `workflow-execution` | `backend/workers/workflow.py::run_workflow` | 30 | 3 | exp 1s |
| `schedule-tick` | `backend/workers/schedule.py::tick` | 5 | 1 | — |
| `webhook-execution` | `backend/workers/webhook.py::run_webhook` | 20 | 2 | exp 2s |
| `notification-delivery` | `backend/workers/notify.py::deliver` | 10 | 3 | exp 5s |

Each queue runs in its own docker-compose service so they scale independently. Spike in team runs? `docker compose up -d --scale worker-team=10` without touching employee throughput.

---

## 4. Identity model (race-condition prevention)

This is the **single most important change**. Every run gets its own set of IDs distinct from the entity IDs.

### 4.1 ID hierarchy

```
user_id, workspace_id        ← persistent (who owns this)
employee_id, team_id,         ← definition (what is being run)
  sprint_id, workflow_id
───────────────────────────────────────
team_run_id                   ← one per team invocation
employee_run_id               ← one per employee invocation (N per team_run)
execution_id                  ← one per job attempt (= arq job_id)
step_id                       ← one per ReAct step
```

**Rule:** all Redis keys, logs, DB rows, cancellation flags, messaging routes → keyed on **run IDs**. Entity IDs only appear as FKs for "list all runs of employee X" queries.

### 4.2 ID generation

**New file:** `backend/core/ids.py`
```python
from uuid_extensions import uuid7  # time-sortable

def new_employee_run_id() -> str: return f"er_{uuid7()}"
def new_team_run_id() -> str:     return f"tr_{uuid7()}"
def new_sprint_run_id() -> str:   return f"sr_{uuid7()}"
def new_workflow_run_id() -> str: return f"wr_{uuid7()}"
def new_execution_id() -> str:    return f"ex_{uuid7()}"
```

UUIDv7 = time-ordered → good DB index locality, logs sort chronologically.

### 4.3 ExecutionContext

**New file:** `backend/core/execution/context.py`
```python
from dataclasses import dataclass

@dataclass(frozen=True)  # immutable — never mutate mid-run
class ExecutionContext:
    # persistent identity
    user_id: str
    workspace_id: str
    employee_id: str | None      # definition
    team_id: str | None
    sprint_id: str | None
    workflow_id: str | None

    # per-invocation
    employee_run_id: str | None  # this specific instance
    team_run_id: str | None      # parent team run if any
    sprint_run_id: str | None
    workflow_run_id: str | None
    execution_id: str            # == arq job id
    parent_execution_id: str | None
    attempt: int
```

Children spawned by fan-out inherit parent's `team_run_id` but get a **fresh** `employee_run_id` + `execution_id`.

### 4.4 DB schema (Postgres + pgvector, replaces SQLite)

```sql
-- Definitions (what)
employees          (id, user_id, name, prompt, tools, ...)
teams              (id, user_id, config, ...)
sprints            (id, team_id, goal, ...)
workflows          (id, user_id, dag, ...)

-- Runs (which instance)
team_runs          (id PK, team_id FK, user_id, status, started_at, ended_at, ...)
employee_runs      (id PK, employee_id FK, team_run_id FK?, sprint_run_id FK?,
                    status, started_at, ended_at, snapshot JSONB, ...)
sprint_runs        (id PK, sprint_id FK, team_run_id FK?, status, ...)
workflow_runs      (id PK, workflow_id FK, status, snapshot JSONB, ...)

-- Job-level (retries)
executions         (id PK, employee_run_id FK?, workflow_run_id FK?, attempt,
                    worker_id, status, started_at, ended_at, error, ...)

-- Steps (per ReAct iteration)
employee_run_steps (id, employee_run_id FK, step_no, input, tool_calls,
                    output, llm_usage, started_at, ended_at)

-- Fan-out mapping
team_run_members   (team_run_id FK, employee_run_id FK, PK(both))

-- Messaging (already exists, must move to run IDs)
inter_employee_messages
  (id, from_employee_run_id, to_employee_run_id, team_run_id, body, sent_at)
```

**Critical:** `inter_employee_messages.to_employee_run_id` routes to a specific **instance**. Two parallel instances of the same employee don't cross-wire messages.

### 4.5 Redis key conventions

Always scope on run IDs:

```python
f"cancel:ex:{execution_id}"          # cancel this job attempt
f"cancel:er:{employee_run_id}"       # cancel all attempts in this run
f"cancel:tr:{team_run_id}"           # cascade cancel team
f"cancel:sr:{sprint_run_id}"         # cascade cancel sprint

f"state:er:{employee_run_id}"        # scratch state for resume
f"ctx:ex:{execution_id}:step:{n}"    # per-step snapshot

f"counter:tr:{team_run_id}:pending"  # fan-in countdown
f"counter:tr:{team_run_id}:done"

f"lane:user:{user_id}"               # tenant dispatch lane (LIST)
f"q:global"                          # global depth counter (ZSET)
f"q:user:{user_id}"                  # per-user depth counter

f"inflight:emp:{employee_id}"        # optional: cap concurrent instances per definition
f"idem:{idempotency_key}"            # dedupe retries
```

### 4.6 Logging

**Replace** `backend/core/logging` helpers with a `bind()`-style structured logger (structlog or loguru):

```python
logger = get_logger(__name__).bind(
    user_id=ctx.user_id,
    employee_id=ctx.employee_id,
    employee_run_id=ctx.employee_run_id,
    team_run_id=ctx.team_run_id,
    execution_id=ctx.execution_id,
    attempt=ctx.attempt,
)
```

Grep `employee_run_id=er_...` → one run. Grep `employee_id=emp_...` → all runs of that employee.

---

## 5. Backpressure — three gates

### Gate A: Admission (API pod, in-process)

**New file:** `backend/api/middleware/admission.py`

In-process semaphore. Each pod has `ADMISSION_GATE_MAX_INFLIGHT` (default 500). Returns 429 with `Retry-After` when full. Aggregate ceiling = `N_pods × 500`. Zero external calls — purely protects one pod from being flooded.

### Gate B: Per-tenant dispatcher (Redis)

**New folder:** `backend/core/dispatch/`
- `gate.py` — `enqueue_with_caps()` checks `q:user:{id}` depth vs `DISPATCH_MAX_QUEUE_PER_USER=1000`; checks `q:global` vs `DISPATCH_MAX_QUEUE_GLOBAL=50000`. Raises `QueueFullError` → API returns 503.
- `dispatcher.py` — background loop (runs in `worker-schedule` service) that pulls fairly from per-user lanes into arq queues. Prevents one tenant starving others.
- `types.py` — lane/queue enums.

Mirrors Sim's `lib/core/workspace-dispatch/`.

### Gate C: Worker concurrency (arq)

Each `WorkerSettings.max_jobs` = hard ceiling per process. Combined with replicas = total throughput per queue.

### Optional Gate D: Per-entity concurrency cap

Rate-limited external tools: cap instances of one employee definition.
```python
count = await redis.incr(f"inflight:emp:{employee_id}")
try:
    if count > MAX_PER_EMPLOYEE: raise AtCapacity
    await run(...)
finally:
    await redis.decr(f"inflight:emp:{employee_id}")
```

---

## 6. Cancellation

**New file:** `backend/core/execution/cancellation.py`

Three cancel scopes, checked together in the ReAct loop:

```python
async def should_cancel(ctx: ExecutionContext) -> bool:
    keys = [f"cancel:ex:{ctx.execution_id}"]
    if ctx.employee_run_id: keys.append(f"cancel:er:{ctx.employee_run_id}")
    if ctx.team_run_id:     keys.append(f"cancel:tr:{ctx.team_run_id}")
    if ctx.sprint_run_id:   keys.append(f"cancel:sr:{ctx.sprint_run_id}")
    return await redis.exists(*keys) > 0
```

API endpoints:
| Route | Redis op |
|---|---|
| `DELETE /executions/{execution_id}` | `SET cancel:ex:{id} 1 EX 3600` |
| `DELETE /employee-runs/{id}` | `SET cancel:er:{id} 1 EX 3600` |
| `DELETE /team-runs/{id}` | `SET cancel:tr:{id} 1 EX 3600` |
| `DELETE /sprint-runs/{id}` | `SET cancel:sr:{id} 1 EX 3600` |

Worker polls once per ReAct step + every 500ms during long LLM streams. `abort_signal` pattern from Sim (`engine.ts:75-83`).

---

## 7. Fan-out / fan-in (teams, sprints)

**Replace** `team_runner.py`'s `asyncio.gather` with enqueue-based fan-out:

```python
# backend/workers/team.py
async def run_team(ctx_dict, members: list[Member]):
    ctx = ExecutionContext(**ctx_dict)
    team_run_id = ctx.team_run_id
    await redis.set(f"counter:tr:{team_run_id}:pending", len(members))

    for m in members:
        employee_run_id = new_employee_run_id()
        execution_id    = new_execution_id()
        child_ctx = replace(ctx,
            employee_id=m.employee_id,
            employee_run_id=employee_run_id,
            execution_id=execution_id,
            parent_execution_id=ctx.execution_id,
            attempt=0,
        )
        await arq_pool.enqueue_job(
            "run_employee",
            _queue_name="employee-run",
            _job_id=execution_id,          # idempotency
            ctx_dict=asdict(child_ctx),
            input=m.input,
        )
        await db.execute(
            "INSERT INTO employee_runs (id, employee_id, team_run_id, status) "
            "VALUES ($1,$2,$3,'queued')",
            employee_run_id, m.employee_id, team_run_id,
        )

    # Return — fan-in happens via child completion callback
```

**Fan-in** (employee worker completes):
```python
# at end of run_employee
remaining = await redis.decr(f"counter:tr:{team_run_id}:pending")
if remaining == 0:
    await arq_pool.enqueue_job("aggregate_team", team_run_id=team_run_id,
                               _queue_name="team-run")
```

Same pattern for `sprint-run` → fan out employee children, counter-based fan-in. 20 employees in a team = 20 worker slots used in parallel. 10 pods × 50 concurrency = **500 concurrent employees**.

---

## 8. Idempotency

**New file:** `backend/core/execution/idempotency.py`

On enqueue, caller supplies `idempotency_key` (or auto-derived from request):
```python
if not await redis.set(f"idem:{key}", execution_id, nx=True, ex=24*3600):
    existing = await redis.get(f"idem:{key}")
    return existing  # return previous execution_id — don't double-enqueue
```

arq also gets `_job_id=execution_id` so retries land on the same job slot.

---

## 9. Resumability (snapshots)

Since everything is sequential ReAct (no DAG), snapshots are per-iteration:

- **Employee**: after each ReAct step, persist context + messages to `employee_runs.snapshot` (JSONB) and `ctx:ex:{id}:step:{n}` in Redis. Retry → load latest snapshot, resume from `step_no + 1`.
- **Harry / workflow**: after each **completed task** in the task list, persist `{task_index, task_outputs, messages}` to `workflow_runs.snapshot`. Retry → Harry resumes at `task_index + 1` with prior outputs still available for downstream tasks.
- **Team / sprint**: the parent run only stores which children are `queued/running/done`. Children (employee runs) own their own snapshots. On parent retry, don't re-enqueue children whose `employee_runs.status` is already `running` or `completed`.

---

## 10. File-by-file migration

### New files
```
backend/
  core/
    ids.py                              # UUIDv7 generators
    execution/
      __init__.py
      context.py                        # ExecutionContext dataclass
      cancellation.py                   # 3-scope cancel check
      idempotency.py
      snapshot.py                       # save/load per-run state
    dispatch/
      __init__.py
      gate.py                           # per-user/global caps
      dispatcher.py                     # fair pull from lanes
      types.py
    logging/
      context_logger.py                 # bind()-style structured
  api/
    middleware/
      admission.py                      # in-process semaphore
  workers/
    __init__.py
    employee.py                         # arq: run_employee
    team.py                             # arq: run_team, aggregate_team
    sprint.py                           # arq: run_sprint, aggregate_sprint
    workflow.py                         # arq: run_workflow
    schedule.py                         # arq: schedule tick + dispatcher loop
    webhook.py
    notify.py
    _common.py                          # shared settings, redis pool
```

### Modified files
| File | Change |
|---|---|
| `backend/core/agents/employee/react_agent.py` | Accept `ExecutionContext` param; add `should_cancel()` checks every step; remove entity-ID-keyed state; log with bound context |
| `backend/core/agents/employee/team_runner.py` | Replace `asyncio.gather` with arq `enqueue_job` fan-out + Redis counter fan-in |
| `backend/core/agents/employee/sprint_runner.py` | Same — enqueue-based fan-out |
| `backend/core/workflows/engine/executor.py` | Accept `ExecutionContext`; snapshot after each **task** (not "block" — we have no DAG); check cancellation; emit events via Redis pub/sub |
| `backend/core/workflows/engine/coworker.py` | Harry's ReAct loop accepts `ExecutionContext`; snapshot/cancel check between tasks (iterations of the task list) and inside long LLM streams; route inter-agent messages by `employee_run_id`, not `employee_id` |
| `backend/core/workflows/worker.py` | **Delete.** Replaced by `backend/workers/workflow.py` + `backend/workers/schedule.py` |
| `backend/api/routers/teams.py` | `POST /teams/{id}/run` → generate `team_run_id`, enqueue, return 202 + id |
| `backend/api/routers/employee.py` | Same pattern — enqueue not execute |
| `backend/api/routers/sprints.py` | Same |
| `backend/api/routers/workflows.py` | Same |
| `backend/api/main.py` | Add admission middleware; add Redis lifespan hook |
| `backend/db/database.py` | Switch SQLite → asyncpg Postgres; add run tables |
| `backend/db/stores/*_store.py` | Split entity CRUD from run CRUD; add `employee_run_store`, `team_run_store`, `execution_store` |
| `backend/db/stores/employee_store.py` | Inter-employee messages table switches to run IDs |

### Deletions
- `workflows.db` (SQLite file) — migrated to Postgres
- `backend/core/workflows/worker.py` — replaced

---

## 11. Deployment (docker-compose)

```yaml
services:
  api:
    build: { context: ., dockerfile: docker/api.Dockerfile }
    command: uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      - ADMISSION_GATE_MAX_INFLIGHT=500
      - DISPATCH_MAX_QUEUE_PER_USER=1000
      - DISPATCH_MAX_QUEUE_GLOBAL=50000
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://ceo:ceo@db:5432/ceo_agent
    ports: ['8000:8000']
    depends_on: [redis, db, migrations]
    deploy: { replicas: 2 }

  worker-employee:
    build: { context: ., dockerfile: docker/worker.Dockerfile }
    command: arq backend.workers.employee.WorkerSettings
    environment:
      - WORKER_CONCURRENCY=50
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://ceo:ceo@db:5432/ceo_agent
    depends_on: [redis, db]
    deploy: { replicas: 4 }

  worker-team:
    command: arq backend.workers.team.WorkerSettings
    environment: { WORKER_CONCURRENCY: 20 }
    deploy: { replicas: 2 }

  worker-sprint:
    command: arq backend.workers.sprint.WorkerSettings
    environment: { WORKER_CONCURRENCY: 10 }
    deploy: { replicas: 2 }

  worker-workflow:
    command: arq backend.workers.workflow.WorkerSettings
    environment: { WORKER_CONCURRENCY: 30 }
    deploy: { replicas: 2 }

  worker-schedule:  # also runs the dispatcher loop
    command: arq backend.workers.schedule.WorkerSettings
    deploy: { replicas: 1 }  # singleton

  worker-webhook:
    command: arq backend.workers.webhook.WorkerSettings
    deploy: { replicas: 2 }

  worker-notify:
    command: arq backend.workers.notify.WorkerSettings
    deploy: { replicas: 1 }

  redis:
    image: redis:7-alpine
    volumes: [redis_data:/data]

  db:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: ceo
      POSTGRES_PASSWORD: ceo
      POSTGRES_DB: ceo_agent
    volumes: [pg_data:/var/lib/postgresql/data]

  migrations:
    build: { context: ., dockerfile: docker/migrations.Dockerfile }
    command: alembic upgrade head
    depends_on: [db]
    restart: 'no'

volumes:
  redis_data:
  pg_data:
```

Scale any worker family independently:
```
docker compose up -d --scale worker-employee=10
```

---

## 12. Observability

- **Structured logs**: `user_id`, `employee_run_id`, `team_run_id`, `execution_id`, `attempt` on every line via `logger.bind(**ctx_fields)`.
- **Metrics** (Prometheus via `prometheus_client`):
  - `queue_depth{queue="employee-run"}`
  - `inflight_admission`
  - `employee_run_duration_seconds` histogram
  - `employee_run_failures_total{reason}`
- **Health endpoints** on workers: `GET /health/live`, `/health/ready` → compose/k8s restarts zombies.
- **Tracing**: OpenTelemetry, propagate `execution_id` as trace-id root.

---

## 13. Migration order (minimize risk)

1. **Add Redis + Postgres** to compose. Migrate SQLite → Postgres (`alembic` initial).
2. **Ship `backend/core/ids.py` + `ExecutionContext`**. No behavior change — just threading IDs through the existing code.
3. **Add run tables** (`employee_runs`, `team_runs`, `sprint_runs`, `workflow_runs`, `executions`, `team_run_members`). Dual-write from current paths.
4. **Add structured logging** with bound context. No infra change — sets up for observability later.
5. **Introduce arq + `worker-employee`** with ONE queue. Move `react_agent.py` execution out of the API request. API returns 202 + `execution_id`. Poll for result.
6. **Cancellation module**. Wire `should_cancel()` into ReAct loop step boundary.
7. **Admission gate middleware** (20 lines).
8. **Per-user queue caps** in Redis (dispatcher gate).
9. **Fan-out refactor for teams** → `worker-team` enqueues children. Delete `asyncio.gather` path.
10. **Fan-out refactor for sprints**.
11. **Workflow worker** → `worker-workflow`. Delete `backend/core/workflows/worker.py`.
12. **Snapshot/resume** on top of run tables.
13. **Dispatcher fairness loop** (lane → queue pull).
14. **Metrics + tracing**.

Each step is independently shippable. Old path keeps working until the step that replaces it.

---

## 14. Worked example — 50 users × 10 teams × 20 employees in parallel

- User hits `POST /teams/{id}/run` → API (admission gate, 1 of 500 slots on this pod).
- Dispatcher gate: user queue 5/1000, global 327/50000 → pass. Enqueue `team-run` job with `team_run_id=tr_...`, `execution_id=ex_...`.
- API returns 202 + `team_run_id`. Total API time: ~20ms.
- `worker-team` (20 concurrency × 2 replicas = 40 slots) picks up job. Generates 20 fresh `employee_run_id`s + `execution_id`s. Inserts 20 rows in `employee_runs`. Enqueues 20 `employee-run` jobs. Sets `counter:tr:{team_run_id}:pending = 20`.
- `worker-employee` (50 concurrency × 4 replicas = 200 slots) pulls employee jobs. Each job has its own `ExecutionContext`. Each logs with its own `employee_run_id`. Each checks its own cancellation keys. Zero shared state.
- As each employee finishes: `DECR counter:tr:...:pending`. Last one → enqueues `aggregate_team`.
- Meanwhile 500 users doing the same: 500 × 20 = 10,000 queued employee runs. Workers steady-state 200 concurrent. Rest wait in Redis — zero API impact.

No races because:
- Every instance has unique `employee_run_id` → unique Redis keys → unique log stream.
- Inter-employee messages route to `employee_run_id`, not `employee_id`.
- Cancellation by `execution_id` kills only that attempt; by `employee_run_id` kills that instance; by `team_run_id` cascades.
- Retries reuse `execution_id` (arq `_job_id`) → idempotent.

---

## 15. Golden rules (non-negotiable)

1. **API never executes agent/workflow code.** Enqueue only, return 202.
2. **Run IDs scope everything.** Redis keys, logs, DB rows, messages, cancellation. Entity IDs are FKs only.
3. **ExecutionContext is frozen.** Child jobs get a new context via `dataclasses.replace`.
4. **Every enqueue passes through the dispatcher gate.** No direct `queue.enqueue_job` from routes.
5. **Every long-running step checks cancellation.** ReAct steps, streaming LLM tokens, DAG block completion.
6. **Every worker is replaceable.** No in-memory state — state lives in Postgres + Redis.
7. **Shared-nothing per run.** No globals, no module-level caches keyed by entity ID.

---

## 16. Reference

- Sim architecture: `.reference/sim/apps/sim/`
  - Execution engine: `executor/execution/engine.ts`
  - Parallel orchestrator: `executor/orchestrators/parallel.ts`
  - Worker: `worker/index.ts`
  - Queues: `lib/core/bullmq/queues.ts`
  - Admission: `lib/core/admission/gate.ts`
  - Dispatcher: `lib/core/workspace-dispatch/`
  - Cancellation: `lib/execution/cancellation.ts`
  - docker-compose: `.reference/sim/docker-compose.prod.yml`

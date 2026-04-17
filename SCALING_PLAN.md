# ceo-agent Scaling Migration Plan (Temporal OSS + Postgres + Redis)

> **For the implementing agent (Codex):** follow phases in order. Do **NOT** modify agent ReAct logic, Harry workflow executor, prompts, or tool implementations. Only wrap them. Every phase must be independently runnable and tested before proceeding to the next.

## Golden Rules (do not violate)

1. **DO NOT** modify the ReAct loop logic in `backend/core/agents/employee/react_agent.py`.
2. **DO NOT** modify Harry in `backend/core/workflows/engine/coworker.py` or `executor.py`.
3. **DO NOT** change tool implementations in `backend/core/tools/`.
4. **DO NOT** change prompts, system messages, or LLM call shapes.
5. **DO NOT** delete or rename existing public functions; only add wrappers.
6. All new code goes in **new files/modules**. Existing files get **minimal** edits (entrypoint wiring only).
7. Preserve existing REST contracts — frontend must keep working unchanged at every phase.
8. Each phase ends with: (a) app starts, (b) an existing end-to-end happy path works, (c) new tests pass.

---

## Phase 0 — Baseline & Instrumentation

**Goal:** measure current behavior, add tracing, no functional change.

### Tasks
- Create `backend/core/observability/` package.
  - `tracing.py` — OpenTelemetry init (OTLP exporter, env-driven endpoint).
  - `metrics.py` — Prometheus client (counters/histograms registry).
- Add decorators `@traced("name")` and `@timed("name")` usable on any function.
- Instrument:
  - `backend/core/agents/employee/react_agent.py` — wrap the public `run()` method **only** with `@traced`. Do NOT touch internals.
  - `backend/core/workflows/engine/coworker.py` — wrap the public `execute()` entrypoint.
  - `backend/core/tools/catalog.py` — wrap the tool dispatch function.
  - `backend/services/llm_provider.py` — wrap LLM call.
- Add `/metrics` endpoint in `backend/api/main.py` (Prometheus scrape).
- Add env vars to `.env.example`: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME=ceo-agent-api`.

### Deliverable
- `GET /metrics` returns Prometheus text.
- Starting an agent run produces traces visible in console exporter (fallback if no OTLP configured).

### Acceptance
- Existing `GET /api/employees`, chat, and team run endpoints still work unchanged.

---

## Phase 1 — Postgres Migration (replace SQLite)

**Goal:** move from `workflows.db` (SQLite) to Postgres. Zero logic changes above the store layer.

### Tasks
- Add dependency: `asyncpg`, `sqlalchemy[asyncio]`, `alembic`, `psycopg2-binary`.
- New file: `backend/db/postgres.py` — async engine, session factory, connection pool settings (PgBouncer-friendly: `pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`).
- Create `backend/db/migrations/` with Alembic init.
- Generate initial migration reflecting **current** SQLite schema (inspect `backend/db/database.py` and every store in `backend/db/stores/`).
- **Add `tenant_id TEXT` column** to every table now (nullable, default `'default'`). Even if unused today, this is cheap to add now and expensive later.
- Rewrite each store to use async SQLAlchemy while **keeping the exact same public method signatures**:
  - `backend/db/stores/auth_store.py`
  - `backend/db/stores/employee_store.py`
  - `backend/db/stores/workflow_store.py`
  - `backend/db/stores/team_store.py`
  - `backend/db/stores/sprint_store.py`
  - `backend/db/stores/file_store.py`
- Write a one-shot migration script `scripts/sqlite_to_postgres.py` that dumps SQLite rows and inserts into Postgres.
- Add indexes: `(tenant_id, created_at)` on all time-series tables; `(run_id, status)` on runs; `(employee_id, updated_at)` on employees.
- Env vars: `DATABASE_URL=postgresql+asyncpg://...`.
- `docker-compose.yml` at repo root with `postgres:16` + `pgbouncer` services for local dev.

### Deliverable
- App runs against Postgres. All existing routes pass smoke tests.
- Migration script copies existing `workflows.db` into Postgres cleanly.

### Acceptance
- CRUD on employees, teams, workflows, sprints, files all work.
- Existing frontend unchanged and functional.

---

## Phase 2 — Redis & Stateless API Pods

**Goal:** introduce Redis; move SSE to pub/sub so multiple API pods work.

### Tasks
- Add dependency: `redis[hiredis]>=5`.
- New file: `backend/core/bus/redis_bus.py`:
  - `publish(channel, event)`, `subscribe(channel)` async helpers.
  - Connection pool singleton.
- New file: `backend/core/bus/events.py` — event schemas: `RunStartedEvent`, `AgentTurnEvent`, `ToolCallEvent`, `RunCompletedEvent`, `MessageEvent`.
- Identify current SSE emitters (search for `EventSourceResponse` or `sse` in `backend/api/routers/`, especially `teams.py`, `workflows.py`, `chat.py`).
  - For each in-process event emission, **also** publish to Redis channel `run:{run_id}` and `team:{team_id}`.
  - Rewrite SSE endpoints to subscribe to Redis instead of in-process queues.
- New file: `backend/core/bus/rate_limit.py`:
  - Token-bucket Lua script for per-tenant LLM rate limiting. Key: `rl:tenant:{id}:llm:{provider}`.
  - Callable as `await check_and_consume(tenant_id, provider, tokens)`.
- Env vars: `REDIS_URL=redis://localhost:6379/0`.
- `docker-compose.yml` add `redis:7` service.

### Deliverable
- Running two API pods behind a load balancer, SSE still works for any client regardless of which pod runs the agent.

### Acceptance
- Start team run on pod A; stream progress from pod B. Works.

---

## Phase 3 — Temporal OSS Integration (the big one)

**Goal:** wrap agent runs and Harry in Temporal workflows. **Core logic untouched.**

### 3.1 Infra setup
- Add dependency: `temporalio>=1.7`.
- `docker-compose.yml` add `temporal`, `temporal-ui`, and a dedicated `temporal-postgres` (separate from app Postgres).
- Env vars: `TEMPORAL_HOST=localhost:7233`, `TEMPORAL_NAMESPACE=ceo-agent`.

### 3.2 Package layout
Create `backend/core/orchestration/`:
```
orchestration/
├── __init__.py
├── client.py              # Temporal client singleton
├── worker.py              # Worker process entrypoint
├── workflows/
│   ├── __init__.py
│   ├── agent_workflow.py
│   ├── team_run_workflow.py
│   ├── harry_workflow.py
│   └── scheduled_job_workflow.py
└── activities/
    ├── __init__.py
    ├── agent_activities.py
    ├── harry_activities.py
    └── tool_activities.py
```

### 3.3 Activities (thin wrappers — DO NOT re-implement logic)

`activities/agent_activities.py`:
- `run_agent_activity(employee_id, goal, team_id=None, run_id=None, tenant_id=None)`:
  - Instantiate `GenericEmployeeAgent` from `backend/core/agents/employee/react_agent.py` with existing constructor.
  - Call its existing `run(goal)` method.
  - Publish progress events to Redis bus (Phase 2) so UI sees them.
  - Return the result dict as-is.

`activities/harry_activities.py`:
- `run_harry_workflow_activity(workflow_id, inputs, tenant_id=None)`:
  - Call existing Harry entrypoint in `backend/core/workflows/engine/coworker.py`.
  - No logic changes to Harry.

`activities/tool_activities.py`:
- Optional at this phase — tools can stay inside agent activity for now. Add stubs for future per-tool activities but do not wire them in.

### 3.4 Workflows

`workflows/agent_workflow.py`:
- `AgentWorkflow.run(employee_id, goal, team_id, run_id, tenant_id)`:
  - Retry policy: `maximum_attempts=3`, non-retryable on validation errors.
  - Activity timeout: `start_to_close=30min`.
  - Calls `run_agent_activity` once. (Whole-loop-as-one-activity strategy — see Golden Rule #1.)

`workflows/team_run_workflow.py`:
- `TeamRunWorkflow.run(team_id, goal, member_tasks, tenant_id)`:
  - Uses `asyncio.gather` over `workflow.execute_child_workflow(AgentWorkflow, ...)` per member.
  - Accepts signals: `cancel`, `pause`, `add_message`.
  - Exposes query: `get_status`.

`workflows/harry_workflow.py`:
- Single-activity wrapper around `run_harry_workflow_activity`.

`workflows/scheduled_job_workflow.py`:
- Thin wrapper so Temporal Schedules can invoke any of the above on cron.

### 3.5 Worker process
`orchestration/worker.py`:
- Registers all workflows and activities.
- Task queues: `agent-q`, `tool-q`, `harry-q`.
- Concurrency: `max_concurrent_activities=50` default, overridable by env.
- Entrypoint: `python -m backend.core.orchestration.worker`.

### 3.6 API wiring (entrypoint swap only)
Edit these files — **entrypoints only**, no logic changes:
- `backend/api/routers/teams.py`:
  - In the handler that starts a team run, replace direct `TeamRunner` call with `temporal_client.start_workflow(TeamRunWorkflow, ...)`.
  - Return `run_id` from workflow handle.
- `backend/api/routers/workflows.py`:
  - For Harry workflow triggers, start `HarryWorkflow` via Temporal.
- `backend/api/routers/chat.py`:
  - For single-agent chat runs, start `AgentWorkflow` via Temporal.
- Keep the **old paths** behind a feature flag env var `USE_TEMPORAL=true|false` so rollback is one env var.

### 3.7 Scheduled jobs
- Find current cron logic in `backend/core/tools/system_tools/cronjob_tool.py`.
- Add a one-time script `scripts/migrate_crons_to_temporal.py` that reads existing cron rows and creates Temporal Schedules.
- New cron creation goes through Temporal Schedules API; keep DB row as metadata only.

### Deliverable
- `docker-compose up` brings up Postgres, Redis, Temporal, Temporal UI, API pod(s), worker pod(s).
- Starting an agent run via API creates a workflow visible in Temporal UI at `http://localhost:8233`.
- Killing the worker pod mid-run: Temporal retries on restart; run completes.

### Acceptance
- All existing user flows work identically from the frontend's perspective.
- Temporal UI shows workflow history for each run.
- With `USE_TEMPORAL=false`, old path still works (rollback path).

---

## Phase 4 — Per-Tenant Fairness & Autoscaling

**Goal:** multi-tenant safety; workers autoscale on queue depth.

### Tasks
- Add `tenant_id` propagation everywhere: JWT claim → request context → workflow input → activity input → Redis rate-limit key.
- In `activities/agent_activities.py`, before each LLM call inside the activity, call `rate_limit.check_and_consume(tenant_id, 'anthropic', estimated_tokens)`. On exceed, raise a **retryable** error — Temporal backs off automatically.
- Per-tenant cost cap: new table `tenant_budget(tenant_id, daily_limit_usd, spent_today_usd)`. Activity checks before LLM call; raises non-retryable if exceeded.
- Kubernetes manifests in `deploy/k8s/`:
  - `api-deployment.yaml`, `worker-agent-deployment.yaml`, `worker-harry-deployment.yaml`, `ws-gateway-deployment.yaml`.
  - KEDA `ScaledObject` for workers using `temporal-cloud` scaler (OSS equivalent: poll Temporal task queue backlog via metrics).
- Helm chart in `deploy/helm/ceo-agent/` with values for dev/staging/prod.

### Acceptance
- Hitting one tenant with 100 concurrent requests does not starve other tenants.
- Exceeding daily budget halts new runs with a clear error; in-flight completes.

---

## Phase 5 — Hardening

### Tasks
- **Secrets**: move API keys from `.env` to AWS Secrets Manager / Vault; load at pod startup.
- **Circuit breaker**: wrap LLM provider and external tool HTTP calls with `purgatory` or custom breaker. Keys per provider.
- **Dead-letter**: configure Temporal `maximum_attempts` + on-final-failure, write run to `failed_runs` table with full event history JSON.
- **Prompt injection**: output sanitizer on tool results before they re-enter agent context (allowlist + max length).
- **Consistent-hash LLM routing**: hash `run_id` → pick LLM worker; improves Anthropic prompt-cache hit rate.
- **Load test**: `scripts/loadtest/` with k6 scenarios for: 100 concurrent team runs, 1000 chat messages/sec, 10k scheduled workflows.
- **Chaos test**: `scripts/chaos/` — kills random worker pods during active runs, asserts completion.
- **Runbooks**: `docs/runbooks/` — LLM outage, Temporal down, Postgres failover, runaway workflow.

---

## File-Reference Inventory (for implementer sanity check)

### Files that MUST NOT change semantically
- `backend/core/agents/employee/react_agent.py`
- `backend/core/workflows/engine/coworker.py`
- `backend/core/workflows/engine/executor.py`
- `backend/core/tools/catalog.py`
- `backend/core/tools/employee_tools/*`
- `backend/core/tools/integration_tools/*`
- `backend/core/tools/system_tools/*`
- `backend/services/llm_provider.py`, `llm_config.py`, `prompt_generator.py`

Allowed change: adding `@traced` / `@timed` decorators only (Phase 0).

### Files that will be modified (entrypoints only)
- `backend/api/main.py` — add `/metrics`, Temporal client init, Redis init.
- `backend/api/routers/teams.py` — swap TeamRunner call for Temporal start.
- `backend/api/routers/workflows.py` — swap Harry call for Temporal start.
- `backend/api/routers/chat.py` — swap direct agent call for Temporal start.
- `backend/db/database.py` — redirect to Postgres async engine.
- `backend/db/stores/*.py` — rewritten to async SQLAlchemy, **same public API**.

### New packages/files
- `backend/core/observability/{tracing,metrics}.py`
- `backend/core/bus/{redis_bus,events,rate_limit}.py`
- `backend/core/orchestration/{client,worker}.py`
- `backend/core/orchestration/workflows/*.py`
- `backend/core/orchestration/activities/*.py`
- `backend/db/postgres.py`
- `backend/db/migrations/` (Alembic)
- `scripts/sqlite_to_postgres.py`
- `scripts/migrate_crons_to_temporal.py`
- `scripts/loadtest/`, `scripts/chaos/`
- `deploy/k8s/`, `deploy/helm/`
- `docker-compose.yml` (root)

### Frontend
- **No changes required** through Phase 3. Frontend may optionally migrate SSE → WebSocket in Phase 4; not mandatory.

---

## Verification Checklist (for post-implementation review)

When reviewing Codex's implementation, confirm each item:

### Phase 0
- [ ] `/metrics` endpoint returns Prometheus format.
- [ ] `react_agent.py` has only decorator additions, no logic edits (verify via `git diff`).
- [ ] Traces appear in console or OTLP endpoint for an agent run.

### Phase 1
- [ ] App connects to Postgres, SQLite file no longer opened at runtime (grep for `sqlite3.connect` should be gone or gated).
- [ ] Every store method keeps the same signature (grep for store method defs; diff against baseline).
- [ ] Alembic migration runs cleanly on empty DB.
- [ ] `scripts/sqlite_to_postgres.py` copies existing data.
- [ ] `tenant_id` column present on all app tables.

### Phase 2
- [ ] `redis` service in docker-compose.
- [ ] SSE endpoints subscribe to Redis, not in-process queues (grep for old `asyncio.Queue` in routers).
- [ ] Two API pods: event published on pod A reaches client connected to pod B.

### Phase 3
- [ ] `backend/core/orchestration/` exists with workflows + activities split.
- [ ] `react_agent.py` and `coworker.py` show **no logic diff** vs baseline (critical!).
- [ ] Activities are thin wrappers (< 30 lines each).
- [ ] `USE_TEMPORAL=false` still runs old path (rollback works).
- [ ] Temporal UI shows AgentWorkflow, TeamRunWorkflow, HarryWorkflow after triggering each.
- [ ] Killing worker pod mid-run → Temporal retries → run completes.
- [ ] `python -m backend.core.orchestration.worker` starts and registers all workflows.

### Phase 4
- [ ] `tenant_id` threads through every activity input.
- [ ] Rate limit Lua script atomic (test with 1000 concurrent calls, verify no over-consumption).
- [ ] KEDA scales workers up on queue backlog, down on idle.

### Phase 5
- [ ] No API keys in `.env.example` other than placeholders.
- [ ] Load test results documented in `docs/load-test-results.md`.
- [ ] Chaos test passes: kill random worker every 30s for 10min, all runs complete.

---

## Rollback Plan (per phase)

- **Phase 0**: remove decorator imports. Zero risk.
- **Phase 1**: keep SQLite files; flip `DATABASE_URL` back to SQLite URL; revert stores to sync versions via git.
- **Phase 2**: set `USE_REDIS_BUS=false`; routers fall back to in-process queues (keep old code path gated, don't delete until Phase 5).
- **Phase 3**: set `USE_TEMPORAL=false`. Old direct-call paths still exist.
- **Phase 4**: disable rate-limit middleware via env flag.
- **Phase 5**: each hardening item independently toggleable.

---

## Non-goals (explicitly out of scope for this migration)

- Rewriting the ReAct loop for per-iteration durability.
- Changing prompts, tool signatures, or agent behavior.
- Frontend refactor (beyond optional WebSocket swap in Phase 4).
- Replacing Anthropic/OpenAI with self-hosted models.
- Multi-region deployment (Phase 5+ future work).

---

## Tech choices locked in

| Layer | Choice | Rationale |
|---|---|---|
| Orchestration | **Temporal OSS** | Durable, agent-friendly, free, self-hostable |
| App DB | **Postgres 16** | Mature, partitioning, pgvector available |
| Cache / Bus | **Redis 7** | Pub/sub + rate-limit Lua + hot state |
| Queue | **Temporal task queues** | No separate broker needed |
| Vector search | **pgvector** (Phase 5) | Reuse Postgres, no new dep |
| Deploy | **Kubernetes + Helm + KEDA** | Standard, autoscaling on queue depth |
| Observability | **OpenTelemetry + Prometheus + Grafana + Tempo** | OSS, vendor-neutral |
| Secrets | **Vault** or **AWS Secrets Manager** | Phase 5 |

Celery is **not** used. Temporal handles all scheduling, retries, and durability.

# Worklone Architecture

Worklone is a Docker-first, self-hosted platform for creating and operating AI employees. This document reflects the current runtime architecture in this repository.

![Worklone Self-Learning Employee Architecture](../frontend/public/research/employee-architecture-diagram.png)

---

## Runtime Topology

Default `docker compose` stack:

- `frontend` (Vite/React) on `:3000`
- `backend` (FastAPI/Uvicorn) on `:8000`
- `redis` on `:6379` (dispatch queues, leases, realtime signals)

Persistent state:

- SQLite database at `/app/data/workflows.db` (mounted volume)
- Redis append-only persistence (`redis-data` volume)

---

## Backend Architecture

Backend entrypoint: `backend/api/main.py`

Main layers:

1. API routers (`backend/api/routers/`)
- `auth`, `chat`, `employees`, `workflows`, `teams`, `sprints`, `dashboard`
- `integrations` (OAuth + integration status)
- `settings` (LLM config, onboarding, password)
- `files`, `skills`, `dispatch`

2. Services (`backend/services/`)
- Employee chat/service orchestration
- Prompt + skill generation
- LLM provider/config resolution

3. Core engine (`backend/core/`)
- ReAct employee agents
- Tool catalog and execution
- Workflow DAG execution engine
- Dispatch layer (queueing, leases, worker coordination)

4. Stores (`backend/db/stores/`)
- `AuthDB`, `EmployeeStore`, `WorkflowStore`, `TeamStore`, `SprintStore`, `FileStore`
- Shared SQLite database with owner-scoped records

---

## LLM Configuration Model

LLM settings are user-scoped and stored in `credentials`.

Key behavior:

- Users set provider/API key/model from Settings or onboarding
- Runtime resolves from per-user credentials first
- Environment values are fallback/default only

Supported provider configuration endpoints:

- `GET /api/settings/llm/providers`
- `GET /api/settings/llm`
- `PUT /api/settings/llm`

---

## Integration Credential Model

Deployment mode is controlled by `DEPLOYMENT_MODE`.

- `self_hosted`: each user stores provider OAuth client ID/secret in their own credential namespace
- `cloud`: backend uses server-managed `PROVIDER_*` environment credentials

This keeps open-source/self-hosted use secure while preserving managed-hosting behavior.

---

## Data and File Storage

Primary DB:

- `workflows.db` (users, sessions, credentials, employees, workflows, teams, sprints, executions, profiles, etc.)

Files:

- Metadata in SQLite table `file_metadata`
- File bytes in `backend/storage/blobs` at runtime path `/app/backend/storage/blobs`

Note: in current compose, DB is volume-mounted; blob directory persistence depends on your compose mount strategy.

---

## Execution Flows

### Employee Chat Flow

1. Frontend sends chat request to `/api/employees/{id}/chat` (or stream endpoint)
2. Backend acquires employee lease via Redis dispatch
3. ReAct loop runs: reasoning → tool calls → observations → final response
4. Background evolution updates user memory/learned skills asynchronously
5. Lease released and presence updated

### Workflow Flow

1. Trigger/API request creates execution
2. Worker/engine builds DAG and resolves variables
3. Blocks execute (agent/tool/function/http/condition/loop/parallel/etc.)
4. Execution state/results persisted in SQLite

### Presence/Dispatch Flow

- Redis stores queue + lease state
- Presence endpoints read lease snapshots
- Frontend polls bulk status for live employee state

---

## Frontend Architecture

Frontend root: `frontend/src`

- Route shell in `App.tsx`
- Auth context/session handling
- Pages for chat, employees, teams, sprints, workflows, integrations, files, research, legal
- Onboarding flow gates authenticated users until required profile + LLM setup is complete

---

## Security and Isolation

- Owner-scoped records for multi-tenant separation
- Session token auth + API key support
- User-scoped credentials for LLM and self-hosted integration secrets
- CORS controlled via env + defaults

---

## Deployment Notes

Recommended startup:

```bash
./scripts/docker-up.sh
```

Manual:

```bash
docker compose up --build
```

The root README is the source for installation/run instructions.

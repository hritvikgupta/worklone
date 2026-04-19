# Backend — Worklone API

FastAPI backend for Worklone self-learning employees.

> License notice: non-commercial research and evaluation only. See [../LICENSE](../LICENSE).

## Runtime

The backend is intended to run via root Docker Compose.

From repository root:

```bash
./scripts/docker-up.sh
```

Backend endpoints:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `GET /health`

## Key Modules

- `backend/api/` — routers and API entrypoints
- `backend/services/` — orchestration and provider logic
- `backend/core/` — agents, tools, workflows, dispatch
- `backend/db/` — SQLite stores
- `backend/lib/` — auth + OAuth helpers

## Storage

- SQLite DB: `/app/data/workflows.db` (volume in Docker)
- File metadata: `file_metadata` table
- File blobs: `/app/backend/storage/blobs`

## LLM & Integrations

- User-scoped LLM provider/key/model in settings/onboarding
- Deployment modes:
  - `self_hosted`: user-supplied OAuth client credentials
  - `cloud`: server-managed `PROVIDER_*` credentials

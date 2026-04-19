# Frontend — Worklone UI

React + TypeScript + Vite frontend for Worklone.

> License notice: non-commercial research and evaluation only. See [../LICENSE](../LICENSE).

## Runtime

Run the full platform from repository root (recommended):

```bash
./scripts/docker-up.sh
```

Frontend URL:

- `http://localhost:3000`

## Frontend Scope

- Auth and onboarding
- Employee chat and provisioning
- Teams, sprints, workflows, files
- Integrations and settings
- Research and legal pages

## Environment

The frontend reads backend URL through `VITE_BACKEND_URL`.
In Docker Compose this is configured automatically.

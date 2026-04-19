# Workflow Engine (Internal Reference)

This folder contains Worklone's DAG workflow runtime used by the backend API.

## Scope

- workflow data models
- DAG build/execution logic
- block handlers
- scheduling helpers
- execution worker integration

## Runtime Context

Workflows are executed through the main backend service and persisted in shared SQLite.
Dispatch and realtime coordination use Redis in Docker deployments.

## Source of Truth

For product-level workflow behavior and API usage, use:

- `docs/WORKFLOWS.md`
- `docs/API_REFERENCE.md`
- `/docs` in the running backend (`http://localhost:8000/docs`)

## Notes

This README intentionally avoids legacy standalone examples so it stays aligned with the current integrated Worklone architecture.

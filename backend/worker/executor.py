"""
Job execution adapters — translate a DispatchJob into a call into the existing
runners without modifying the ReAct loop code.

Each adapter:
  - Receives a DispatchJob.
  - Optionally mutates the job.run_id once the underlying system assigns one.
  - Runs to completion (awaits the runner's end-of-run signal).
  - Returns a result dict (stored on the job for UI inspection).

NONE of these functions touch `react_agent.py` or `coworker.py`. They only
invoke TeamRunner/SprintRunner/WorkflowExecutor — the same classes the old
FastAPI routes used, just invoked from a different process.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.core.dispatch.jobs import DispatchJob

logger = logging.getLogger("worker.executor")


# ─── TEAM ─────────────────────────────────────────────────────────────────────

async def run_team_job(job: DispatchJob) -> dict[str, Any]:
    from backend.core.agents.employee.team_runner import TeamRunner
    from backend.db.stores.team_store import TeamStore
    from backend.core.agents.employee.types import TeamRunStatus

    team_id = job.payload["team_id"]
    goal = job.payload.get("goal", "")
    member_tasks = job.payload.get("member_tasks") or {}
    conversation_id = job.payload.get("conversation_id")

    runner = TeamRunner(team_id=team_id, owner_id=job.owner_id)
    # runner.start() creates the run, records it in TeamStore, then spawns
    # topology execution as a background asyncio.Task. We wait for that task
    # to finish before returning, so the worker holds the lease for the real
    # duration of the run.
    run_id = await runner.start(
        goal=goal,
        member_tasks=member_tasks,
        conversation_id=conversation_id,
        user_id=job.user_id or "anonymous",
    )
    job.run_id = run_id

    # Poll the TeamStore for terminal status (runner spawned the work as a
    # fire-and-forget task; this is the simplest observation point that
    # doesn't require modifying runner internals).
    store = TeamStore()
    terminal = {TeamRunStatus.COMPLETED, TeamRunStatus.FAILED}
    while True:
        run = store.get_run(run_id)
        if run and run.status in terminal:
            break
        await asyncio.sleep(1.0)
    return {"run_id": run_id, "status": run.status.value if run else "unknown"}


# ─── SPRINT ───────────────────────────────────────────────────────────────────

async def run_sprint_job(job: DispatchJob) -> dict[str, Any]:
    from backend.core.agents.employee.sprint_runner import SprintRunner
    from backend.db.stores.sprint_store import SprintStore

    sprint_id = job.payload["sprint_id"]
    task_id = job.payload["task_id"]

    runner = SprintRunner(sprint_id=sprint_id, owner_id=job.owner_id)
    run_id = await runner.start(task_id=task_id, user_id=job.user_id or "anonymous")
    job.run_id = run_id

    store = SprintStore()
    terminal = {"done", "failed", "cancelled"}
    while True:
        runs = store.list_runs_for_task(task_id)
        found = next((r for r in runs if r.get("id") == run_id or r.get("run_id") == run_id), None)
        if found and (found.get("status") in terminal):
            return {"run_id": run_id, "status": found.get("status")}
        await asyncio.sleep(1.0)


# ─── WORKFLOW ─────────────────────────────────────────────────────────────────

async def run_workflow_job(job: DispatchJob) -> dict[str, Any]:
    from datetime import datetime

    from backend.core.dispatch.events import run_progress
    from backend.core.workflows.engine.coworker import CoWorkerAgent
    from backend.core.workflows.types import ExecutionResult, WorkflowStatus, WorkflowTaskStatus
    from backend.core.workflows.utils import generate_id
    from backend.db.stores.workflow_store import WorkflowStore

    workflow_id = job.payload["workflow_id"]
    trigger_type = job.payload.get("trigger_type", "manual")

    store = WorkflowStore()

    exec_id = generate_id("exec")
    exec_result = ExecutionResult(
        execution_id=exec_id,
        workflow_id=workflow_id,
        owner_id=job.owner_id,
        status=WorkflowStatus.RUNNING,
        trigger_type=trigger_type,
        trigger_input={},
        started_at=datetime.now(),
    )
    store.save_execution(exec_result)
    store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING.value)
    job.run_id = exec_id

    agent = CoWorkerAgent(owner_id=job.owner_id)
    success = True
    try:
        async for event in agent.execute_workflow(
            workflow_id, trigger_input={}, stream=True, emit_events=True,
        ):
            if isinstance(event, dict):
                if event.get("type") == "error":
                    success = False
                    exec_result.error = event.get("message", "")
                await run_progress(
                    exec_id,
                    job_id=job.id,
                    user_id=job.user_id,
                    phase=str(event.get("type") or "event"),
                    data=event,
                )
    except Exception as exc:  # noqa: BLE001
        success = False
        exec_result.error = f"{type(exc).__name__}: {exc}"
        logger.exception("workflow job %s failed: %s", job.id, exc)

    now = datetime.now()
    exec_result.completed_at = now
    exec_result.execution_time = (now - exec_result.started_at).total_seconds()

    final_wf = store.get_workflow(workflow_id) or store.get_workflow(workflow_id, job.owner_id)
    if final_wf:
        if success and final_wf.status != WorkflowStatus.FAILED:
            final_wf.status = WorkflowStatus.ACTIVE
            exec_result.status = WorkflowStatus.COMPLETED
            exec_result.output = {"message": "Workflow completed successfully"}
            for t in final_wf.tasks:
                if t.status.value == "running":
                    t.status = WorkflowTaskStatus.COMPLETED
                    if not t.result:
                        t.result = "Completed."
        else:
            final_wf.status = WorkflowStatus.FAILED
            exec_result.status = WorkflowStatus.FAILED
            for t in final_wf.tasks:
                if t.status.value == "running":
                    t.status = WorkflowTaskStatus.FAILED
        store.save_workflow(final_wf)

    store.save_execution(exec_result)

    return {
        "run_id": exec_id,
        "status": exec_result.status.value if hasattr(exec_result.status, "value") else str(exec_result.status),
    }


# ─── Dispatch by kind ─────────────────────────────────────────────────────────

async def execute(job: DispatchJob) -> dict[str, Any]:
    if job.kind == "team":
        return await run_team_job(job)
    if job.kind == "sprint":
        return await run_sprint_job(job)
    if job.kind == "workflow":
        return await run_workflow_job(job)
    raise ValueError(f"unknown job kind: {job.kind}")

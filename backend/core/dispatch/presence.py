"""
Presence — lease-derived EmployeeStatus.

Single source of truth for "is Alex busy right now?". Reads Redis leases
and maps them to the EmployeeStatus enum used elsewhere in the codebase.

The DB column on Employee (`status`) is now advisory only. For any live
UI check, call `get_status` / `get_statuses` here.
"""

from __future__ import annotations

from typing import Iterable

from backend.core.agents.employee.types import EmployeeStatus
from backend.core.dispatch.config import k_job
from backend.core.dispatch.leases import lease_owner, snapshot_status
from backend.core.dispatch.redis_client import get_redis
from backend.core.dispatch.jobs import DispatchJob


async def _job_context(job_id: str) -> dict | None:
    """Summarize what the employee is busy on (for tooltips)."""
    raw = await get_redis().get(k_job(job_id))
    if not raw:
        return None
    try:
        job = DispatchJob.from_json(raw)
    except Exception:  # noqa: BLE001
        return None
    return {
        "job_id": job.id,
        "kind": job.kind,  # team | sprint | workflow | chat
        "lane": job.lane,
        "run_id": job.run_id,
        "user_id": job.user_id,
    }


async def get_status(employee_id: str) -> dict:
    """Return {status, busy_in} for a single employee."""
    owner_job = await lease_owner(employee_id)
    if not owner_job:
        return {"employee_id": employee_id, "status": EmployeeStatus.IDLE.value, "busy_in": None}
    ctx = await _job_context(owner_job)
    return {
        "employee_id": employee_id,
        "status": EmployeeStatus.WORKING.value,
        "busy_in": ctx,
    }


async def get_statuses(employee_ids: Iterable[str]) -> dict[str, dict]:
    ids = list(employee_ids)
    if not ids:
        return {}
    snap = await snapshot_status(ids)
    out: dict[str, dict] = {}
    for emp_id, job_id in snap.items():
        if not job_id:
            out[emp_id] = {"employee_id": emp_id, "status": EmployeeStatus.IDLE.value, "busy_in": None}
            continue
        ctx = await _job_context(job_id)
        out[emp_id] = {
            "employee_id": emp_id,
            "status": EmployeeStatus.WORKING.value,
            "busy_in": ctx,
        }
    return out

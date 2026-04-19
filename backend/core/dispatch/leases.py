"""
Employee leases — the core busy-flag system.

A lease is a Redis key `ceo:emp:lease:{employee_id}` whose value is the job id
currently holding that employee, and whose TTL is the maximum time the lease
lives without a heartbeat. While the key exists the employee is BUSY.

Atomic acquisition (acquire_all) is implemented via a Lua script that:
  1. Checks every required employee key: if ANY exists, fails (returns 0).
  2. Checks per-user concurrency: if user is at/above cap, fails.
  3. Otherwise SETs all employee keys with TTL, records the lease set for
     the job (so we can release by job id), and adds job_id to user-running.

Release is non-Lua (pipeline DEL + SREM) because we only release leases we
actually hold (the job_id match prevents clobbering another worker's lease).
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from backend.core.dispatch.config import (
    LEASE_TTL_SECONDS,
    k_emp_lease,
    k_run_leases,
    k_user_running,
)
from backend.core.dispatch.redis_client import get_redis

logger = logging.getLogger("dispatch.leases")


# ─── Atomic admission ─────────────────────────────────────────────────────────
# KEYS layout:
#   KEYS[1] = user_running_set
#   KEYS[2] = run_leases_set (ceo:run:leases:{job_id})
#   KEYS[3..] = employee lease keys
# ARGV layout:
#   ARGV[1] = job_id
#   ARGV[2] = ttl_seconds
#   ARGV[3] = user_concurrency_cap
# Returns: 1 on success, 0 if an employee is busy, -1 if user over cap.

_ACQUIRE_LUA = """
local user_set = KEYS[1]
local run_set = KEYS[2]
local job_id = ARGV[1]
local ttl = tonumber(ARGV[2])
local cap = tonumber(ARGV[3])

-- user concurrency check
local running = redis.call('SCARD', user_set)
if running >= cap then
  return -1
end

-- employee availability check
for i = 3, #KEYS do
  if redis.call('EXISTS', KEYS[i]) == 1 then
    return 0
  end
end

-- grant leases
for i = 3, #KEYS do
  redis.call('SET', KEYS[i], job_id, 'EX', ttl)
  redis.call('SADD', run_set, KEYS[i])
end
redis.call('EXPIRE', run_set, ttl)
redis.call('SADD', user_set, job_id)
return 1
"""


async def acquire_all(
    *,
    job_id: str,
    user_id: str,
    employee_ids: Iterable[str],
    user_cap: int,
    ttl_seconds: int = LEASE_TTL_SECONDS,
) -> int:
    """Try to atomically lease all employees for this job.

    Returns 1 success, 0 busy, -1 user over cap.
    """
    emp_ids = list(dict.fromkeys(employee_ids))  # dedupe, preserve order
    r = get_redis()
    keys = [k_user_running(user_id), k_run_leases(job_id)] + [k_emp_lease(e) for e in emp_ids]
    try:
        res = await r.eval(_ACQUIRE_LUA, len(keys), *keys, job_id, ttl_seconds, user_cap)
        return int(res)
    except Exception as exc:  # noqa: BLE001
        logger.exception("acquire_all failed for job=%s: %s", job_id, exc)
        return 0


async def heartbeat(job_id: str, user_id: str, ttl_seconds: int = LEASE_TTL_SECONDS) -> None:
    """Extend TTL on every employee lease still held by this job."""
    r = get_redis()
    members = await r.smembers(k_run_leases(job_id))
    if not members:
        return
    pipe = r.pipeline()
    for emp_key in members:
        pipe.expire(emp_key, ttl_seconds)
    pipe.expire(k_run_leases(job_id), ttl_seconds)
    await pipe.execute()


async def release_all(job_id: str, user_id: str) -> None:
    """Release every employee lease tagged with this job id.

    Uses a value check — we only DEL the lease key if its value still equals
    our job_id, so a re-issued lease on the same employee won't be stomped.
    """
    r = get_redis()
    members = await r.smembers(k_run_leases(job_id))

    for emp_key in members:
        try:
            # GET + DEL via simple check (race-safe enough for this TTL model).
            current = await r.get(emp_key)
            if current == job_id:
                await r.delete(emp_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("release %s: %s", emp_key, exc)

    pipe = r.pipeline()
    pipe.delete(k_run_leases(job_id))
    pipe.srem(k_user_running(user_id), job_id)
    await pipe.execute()


async def is_employee_busy(employee_id: str) -> bool:
    return bool(await get_redis().exists(k_emp_lease(employee_id)))


async def lease_owner(employee_id: str) -> Optional[str]:
    """Return the job_id currently holding this employee, or None."""
    return await get_redis().get(k_emp_lease(employee_id))


async def snapshot_status(employee_ids: Iterable[str]) -> dict[str, Optional[str]]:
    """Bulk check: {employee_id: job_id_or_None}."""
    ids = list(employee_ids)
    if not ids:
        return {}
    r = get_redis()
    values = await r.mget(*[k_emp_lease(e) for e in ids])
    return dict(zip(ids, values))

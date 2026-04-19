"""Dispatch configuration — all env-tunable knobs in one place."""

import os

# ─── Redis ───
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ─── Lane priorities (lower number = higher priority) ───
LANE_CHAT = "chat"
LANE_SPRINT = "sprint"
LANE_TEAM = "team"
LANE_WORKFLOW = "workflow"

LANES = [LANE_CHAT, LANE_SPRINT, LANE_TEAM, LANE_WORKFLOW]

# ─── Concurrency caps (per-user) ───
DEFAULT_USER_CONCURRENCY = int(os.getenv("DISPATCH_USER_CONCURRENCY", "10"))
GLOBAL_QUEUE_DEPTH = int(os.getenv("DISPATCH_GLOBAL_QUEUE_DEPTH", "5000"))
USER_QUEUE_DEPTH = int(os.getenv("DISPATCH_USER_QUEUE_DEPTH", "500"))

# ─── Lease ───
LEASE_TTL_SECONDS = int(os.getenv("DISPATCH_LEASE_TTL", "900"))  # 15min
LEASE_HEARTBEAT_SECONDS = int(os.getenv("DISPATCH_LEASE_HEARTBEAT", "60"))

# ─── Dispatcher loop ───
DISPATCHER_POLL_MS = int(os.getenv("DISPATCH_POLL_MS", "250"))
DISPATCHER_SCAN_BATCH = int(os.getenv("DISPATCH_SCAN_BATCH", "50"))

# ─── Worker ───
WORKER_CONCURRENCY_PER_LANE = {
    LANE_CHAT: int(os.getenv("WORKER_CHAT_CONCURRENCY", "50")),
    LANE_SPRINT: int(os.getenv("WORKER_SPRINT_CONCURRENCY", "30")),
    LANE_TEAM: int(os.getenv("WORKER_TEAM_CONCURRENCY", "30")),
    LANE_WORKFLOW: int(os.getenv("WORKER_WORKFLOW_CONCURRENCY", "20")),
}

# ─── Redis key prefixes ───
PREFIX = "ceo"
K_JOB_HASH = f"{PREFIX}:job"                          # ceo:job:{job_id} -> JSON
K_WAITING = f"{PREFIX}:waiting"                       # ceo:waiting:{lane} -> ZSET by created_at
K_READY = f"{PREFIX}:ready"                           # ceo:ready:{lane} -> LIST (BRPOP by workers)
K_USER_RUNNING = f"{PREFIX}:user:running"             # ceo:user:running:{user_id} -> SET of job_ids
K_USER_WAITING = f"{PREFIX}:user:waiting"             # ceo:user:waiting:{user_id} -> SET
K_EMP_LEASE = f"{PREFIX}:emp:lease"                   # ceo:emp:lease:{employee_id} -> job_id (TTL)
K_RUN_LEASES = f"{PREFIX}:run:leases"                 # ceo:run:leases:{job_id} -> SET of employee_ids
K_EVENTS = f"{PREFIX}:events"                         # pubsub channel


def q_waiting(lane: str) -> str:
    return f"{K_WAITING}:{lane}"


def q_ready(lane: str) -> str:
    return f"{K_READY}:{lane}"


def k_job(job_id: str) -> str:
    return f"{K_JOB_HASH}:{job_id}"


def k_emp_lease(emp_id: str) -> str:
    return f"{K_EMP_LEASE}:{emp_id}"


def k_user_running(user_id: str) -> str:
    return f"{K_USER_RUNNING}:{user_id or 'anon'}"


def k_user_waiting(user_id: str) -> str:
    return f"{K_USER_WAITING}:{user_id or 'anon'}"


def k_run_leases(job_id: str) -> str:
    return f"{K_RUN_LEASES}:{job_id}"

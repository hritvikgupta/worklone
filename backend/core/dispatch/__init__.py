"""
Dispatch layer — 3-tier job admission + execution system.

Layers:
  1. API routers enqueue jobs (see `jobs.enqueue_job`).
  2. Dispatcher loop admits jobs after leasing required employees.
  3. Worker pool pulls ready jobs and runs the real TeamRunner/SprintRunner/
     WorkflowExecutor/chat code inside a lease heartbeat.

Key primitives:
  - redis_client.get_redis() — shared asyncio Redis client
  - leases.EmployeeLeaseManager — per-employee mutex + heartbeat
  - jobs.JobStore — dispatch_jobs persistence (hash + waiting set)
  - queue.ReadyQueue — per-lane lists consumed by workers
  - events.publish_event / subscribe — Redis pub/sub for socket.io
"""

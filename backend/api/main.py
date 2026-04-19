"""
FastAPI Main Application
"""

import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(override=True)

from backend.api.routes import router
from backend.core.errors import register_exception_handlers
from backend.core.logging import RequestContextMiddleware, configure_logging, get_logger
from backend.db.stores.workflow_store import WorkflowStore
from backend.core.workflows.worker import BackgroundWorker
from backend.core.dispatch.dispatcher import Dispatcher
from backend.core.dispatch.redis_client import close_redis, ping as redis_ping
from backend.realtime.socket_server import asgi_app as socketio_asgi_app, start_bridge, stop_bridge
from backend.worker.main import WorkerPool

configure_logging()

app = FastAPI(
    title="CEO Agent Backend",
    description="Backend API for CEO Agent with Katy PM Assistant",
    version="1.0.0",
)

logger = get_logger("api.main")

# Build CORS origins from defaults + env so OAuth tunnel domains work.
default_origins = {
    "http://localhost:3000",
    "http://localhost:3002",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:5173",
}

env_origins = set()
for key, value in os.environ.items():
    if not value:
        continue
    if key == "FRONTEND_URL" or key.endswith("_FRONTEND_URL"):
        env_origins.add(value.strip())

for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(","):
    normalized = origin.strip()
    if normalized:
        env_origins.add(normalized)

allowed_origins = sorted(default_origins | env_origins)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=os.getenv(
        "CORS_ALLOWED_ORIGIN_REGEX",
        r"https://.*\.trycloudflare\.com",
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)

# Include routes
app.include_router(router, prefix="/api")

# Mount Socket.IO under /socket.io (path in URL, not a subpath prefix)
app.mount("/socket.io", socketio_asgi_app)

workflow_store = WorkflowStore()
workflow_worker = BackgroundWorker(workflow_store)
workflow_worker_task: asyncio.Task | None = None

# Dispatch-layer singletons
dispatcher = Dispatcher()
# Dev mode: run the worker pool inside the API process so `uvicorn backend.api.main:app`
# still works end-to-end without a separate process. Prod should run
# `python -m backend.worker.main` as a separate deployment and set
# RUN_WORKER_IN_API=0 to disable this.
_run_worker_in_api = os.getenv("RUN_WORKER_IN_API", "1") != "0"
worker_pool = WorkerPool() if _run_worker_in_api else None


@app.on_event("startup")
async def start_background_services():
    global workflow_worker_task
    if workflow_worker_task is None or workflow_worker_task.done():
        logger.info("Starting workflow scheduler poller")
        workflow_worker_task = asyncio.create_task(workflow_worker.start())

    # Best-effort Redis availability check (doesn't block startup).
    ok = await redis_ping()
    if not ok:
        logger.warning("Redis is not reachable — dispatch/queue/realtime disabled until it is.")
        return

    logger.info("Starting dispatcher loop")
    await dispatcher.start()
    logger.info("Starting socket.io Redis bridge")
    await start_bridge()
    if worker_pool is not None:
        logger.info("Starting in-process worker pool (dev)")
        await worker_pool.start()


@app.on_event("shutdown")
async def stop_background_services():
    global workflow_worker_task
    logger.info("Stopping workflow scheduler poller")
    await workflow_worker.stop()
    if workflow_worker_task is not None:
        workflow_worker_task.cancel()
        workflow_worker_task = None
    if worker_pool is not None:
        await worker_pool.stop()
    await dispatcher.stop()
    await stop_bridge()
    await close_redis()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

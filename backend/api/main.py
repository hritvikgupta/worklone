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
    # Allow dynamic tunnel hosts if you are rotating Cloudflare/ngrok/localtunnel URLs.
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

workflow_store = WorkflowStore()
workflow_worker = BackgroundWorker(workflow_store)
workflow_worker_task: asyncio.Task | None = None


@app.on_event("startup")
async def start_workflow_worker():
    global workflow_worker_task
    if workflow_worker_task is None or workflow_worker_task.done():
        logger.info("Starting workflow worker")
        workflow_worker_task = asyncio.create_task(workflow_worker.start())


@app.on_event("shutdown")
async def stop_workflow_worker():
    global workflow_worker_task
    logger.info("Stopping workflow worker")
    await workflow_worker.stop()
    if workflow_worker_task is not None:
        workflow_worker_task.cancel()
        workflow_worker_task = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

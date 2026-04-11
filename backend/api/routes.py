"""
API Routes
"""

from fastapi import APIRouter
from backend.routers.chat import router as chat_router
from backend.routers.auth import router as auth_router
from backend.routers.oauth import router as oauth_router
from backend.routers.files import router as files_router
from backend.routers.skills import router as skills_router
from backend.routers.employee import router as employee_router
from backend.routers.workflows import router as workflows_router

router = APIRouter()

# Include all routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(oauth_router, prefix="/integrations", tags=["integrations"])
router.include_router(files_router, prefix="/files", tags=["files"])
router.include_router(skills_router, prefix="/skills", tags=["skills"])
router.include_router(employee_router, tags=["employees"])
router.include_router(workflows_router, tags=["workflows"])

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
from backend.routers.teams import router as teams_router
from backend.routers.sprints import router as sprints_router
from backend.routers.dashboard import router as dashboard_router

router = APIRouter()

# Include all routers
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(oauth_router, prefix="/integrations", tags=["integrations"])
router.include_router(files_router, prefix="/files", tags=["files"])
router.include_router(skills_router, prefix="/skills", tags=["skills"])
router.include_router(employee_router, tags=["employees"])
router.include_router(workflows_router, tags=["workflows"])
router.include_router(teams_router, tags=["teams"])
router.include_router(sprints_router, tags=["sprints"])
router.include_router(dashboard_router, tags=["dashboard"])

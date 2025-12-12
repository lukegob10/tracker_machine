from fastapi import APIRouter

from .routes_projects import router as projects_router
from .routes_phases import router as phases_router
from .routes_solutions import router as solutions_router
from .routes_subcomponents import router as subcomponents_router
from .routes_checklist import router as checklist_router
from .routes_sync import router as sync_router

api_router = APIRouter()
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(solutions_router, tags=["solutions"])
api_router.include_router(phases_router, tags=["phases"])
api_router.include_router(subcomponents_router, tags=["subcomponents"])
api_router.include_router(checklist_router, tags=["checklist"])
api_router.include_router(sync_router, tags=["sync"])

from fastapi import APIRouter, Depends

from .deps import require_user
from .routes_audit import router as audit_router
from .routes_auth import router as auth_router
from .routes_projects import router as projects_router
from .routes_phases import router as phases_router
from .routes_solutions import router as solutions_router
from .routes_subcomponents import router as subcomponents_router
from .routes_sync import router as sync_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

protected_router = APIRouter(dependencies=[Depends(require_user)])
protected_router.include_router(projects_router, prefix="/projects", tags=["projects"])
protected_router.include_router(solutions_router, tags=["solutions"])
protected_router.include_router(phases_router, tags=["phases"])
protected_router.include_router(subcomponents_router, tags=["subcomponents"])
protected_router.include_router(audit_router, tags=["audit"])

api_router.include_router(protected_router)
api_router.include_router(sync_router, tags=["sync"])

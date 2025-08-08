from fastapi import APIRouter
from .system import router as system_router
from .auth import router as auth_router
from .admin import router as admin_router
from .health import router as health_router
from .invitations import router as invitations_router
from .logging import router as logging_router
from .expert import router as expert_router

router = APIRouter(prefix="/v1")
router.include_router(system_router)
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(health_router)
router.include_router(invitations_router)
router.include_router(logging_router)
router.include_router(expert_router)

# app/api/v1/__init__.py
from fastapi import APIRouter

# Import explicite des routers locaux
from .system import router as system_router
from .auth import router as auth_router
from .admin import router as admin_router
from .health import router as health_router
from .invitations import router as invitations_router
from .logging import router as logging_router
from .expert import router as expert_router

# Création d'un routeur principal pour la version 1
router = APIRouter(prefix="/v1")

# Inclusion des sous-routers
router.include_router(system_router, tags=["System"])
router.include_router(auth_router, tags=["Auth"])
router.include_router(admin_router, tags=["Admin"])
router.include_router(health_router, tags=["Health"])
router.include_router(invitations_router, tags=["Invitations"])
router.include_router(logging_router, tags=["Logging"])
router.include_router(expert_router, prefix="/expert", tags=["Expert"])

__all__ = ["router"]

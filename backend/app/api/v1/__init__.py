# app/api/v1/__init__.py
from fastapi import APIRouter

from .system import router as system_router
from .auth import router as auth_router
from .admin import router as admin_router
from .health import router as health_router
from .invitations import router as invitations_router
from .logging import router as logging_router
from .expert import router as expert_router

router = APIRouter(prefix="/v1")

# Ordre logique par domaine
router.include_router(system_router, tags=["System"])
router.include_router(auth_router, tags=["Auth"])
router.include_router(admin_router, tags=["Admin"])
router.include_router(health_router, tags=["Health"])
router.include_router(invitations_router, tags=["Invitations"])
router.include_router(logging_router, tags=["Logging"])

# Expert vit sous /v1/expert/* (pas de prefix dans expert.py)
router.include_router(expert_router, prefix="/expert", tags=["Expert"])

__all__ = ["router"]

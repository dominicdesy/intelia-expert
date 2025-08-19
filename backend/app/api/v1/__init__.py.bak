# app/api/v1/__init__.py - VERSION CORRIGÉE AVEC BILLING
from fastapi import APIRouter

from .system import router as system_router
from .auth import router as auth_router
from .admin import router as admin_router
from .health import router as health_router
from .invitations import router as invitations_router
from .logging import router as logging_router
from .billing import router as billing_router  # 🆕 AJOUTÉ - SYSTÈME DE FACTURATION
from .billing_openai import router as billing_openai_router  # 🔥 NOUVEAU - BILLING OPENAI
from .expert import router as expert_router

# Import conditionnel pour conversations (au cas où le fichier n'existe pas encore)
try:
    from .conversations import router as conversations_router
    CONVERSATIONS_AVAILABLE = True
except ImportError:
    CONVERSATIONS_AVAILABLE = False
    conversations_router = None

router = APIRouter(prefix="/v1")

# Ordre logique par domaine
router.include_router(system_router, tags=["System"])
router.include_router(auth_router, tags=["Auth"])  # 🔧 PAS DE PRÉFIXE (déjà dans auth.py)
router.include_router(admin_router, tags=["Admin"])
router.include_router(health_router, tags=["Health"])
router.include_router(invitations_router, tags=["Invitations"])
router.include_router(logging_router, tags=["Logging"])  # /v1/logging/*
router.include_router(billing_router, tags=["Billing"])  # 🆕 /v1/billing/*
router.include_router(billing_openai_router, prefix="/billing", tags=["Billing-OpenAI"])  # 🔥 NOUVEAU - /v1/billing/openai-*

# Conversations (conditionnel)
if CONVERSATIONS_AVAILABLE:
    router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])

# Expert vit sous /v1/expert/* (pas de prefix dans expert.py)
router.include_router(expert_router, prefix="/expert", tags=["Expert"])

__all__ = ["router"]
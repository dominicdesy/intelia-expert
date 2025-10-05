# -*- coding: utf-8 -*-
"""
api/endpoints.py - Module principal des endpoints API - VERSION MODULAIRE SIMPLE
Importe et combine tous les endpoints depuis les modules séparés
"""

import time
import logging
from utils.types import Dict, Any, Optional
from fastapi import APIRouter
from config.config import BASE_PATH

# Import de TOUS les utilitaires depuis utils (corrige l'import circulaire)
from .utils import (
    safe_serialize_for_json,
    conversation_memory,
    add_to_conversation_memory,
)

# Import du MetricsCollector centralisé depuis utils
from utils.metrics_collector import METRICS as metrics_collector

# Imports des modules d'endpoints
from .endpoints_health import create_health_endpoints
from .endpoints_diagnostic import create_diagnostic_endpoints
from .endpoints_chat import create_chat_endpoints

logger = logging.getLogger(__name__)


# ============================================================================
# CRÉATION DU ROUTER
# ============================================================================


def create_router(services: Optional[Dict[str, Any]] = None) -> APIRouter:
    """Crée le router principal en combinant tous les modules d'endpoints"""

    router = APIRouter()
    _services = services or {}

    def get_service(name: str) -> Any:
        """Helper pour récupérer un service"""
        return _services.get(name)

    # ========================================================================
    # ENDPOINTS DE BASE
    # ========================================================================

    @router.get(f"{BASE_PATH}/version")
    async def version_info():
        """Endpoint de version pour vérifier les déploiements"""
        return {
            "message": "VERSION MODULAIRE - Endpoints séparés",
            "version": "4.1.2-metrics-centralized",
            "timestamp": time.time(),
            "architecture": "modular-endpoints",
            "modules": ["health", "diagnostic", "chat", "utils"],
            "services_count": len(_services),
            "services_list": list(_services.keys()),
            "circular_import_fixed": True,
            "metrics_centralized": True,
        }

    @router.get(f"{BASE_PATH}/deployment-test")
    async def deployment_test():
        """Endpoint de test simple pour confirmer le déploiement"""
        return {
            "message": "ARCHITECTURE MODULAIRE - Endpoints séparés",
            "version": "4.1.2-metrics-centralized",
            "timestamp": time.time(),
            "architecture": "modular-endpoints",
            "files": [
                "endpoints.py",
                "utils.py",
                "endpoints_health.py",
                "endpoints_diagnostic.py",
                "endpoints_chat.py",
            ],
            "circular_import_fixed": True,
            "metrics_centralized": True,
            "metrics_source": "utils.metrics_collector.METRICS",
        }

    # ========================================================================
    # INTÉGRATION DES MODULES
    # ========================================================================

    # Health endpoints
    health_router = create_health_endpoints(_services)
    router.include_router(health_router)

    # Diagnostic endpoints (NOUVEAUX)
    diagnostic_router = create_diagnostic_endpoints(_services)
    router.include_router(diagnostic_router)

    # Chat endpoints
    chat_router = create_chat_endpoints(_services)
    router.include_router(chat_router)

    return router


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "create_router",
    "safe_serialize_for_json",
    "conversation_memory",
    "metrics_collector",
    "add_to_conversation_memory",
]

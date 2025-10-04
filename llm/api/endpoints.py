# -*- coding: utf-8 -*-
"""
api/endpoints.py - Module principal des endpoints API - VERSION MODULAIRE SIMPLE
Importe et combine tous les endpoints depuis les modules séparés
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from collections import deque
from fastapi import APIRouter
from config.config import BASE_PATH

# Import de la fonction utilitaire depuis utils (corrige l'import circulaire)
from .utils import safe_serialize_for_json

# Imports des modules d'endpoints
from .endpoints_health import create_health_endpoints
from .endpoints_diagnostic import create_diagnostic_endpoints
from .endpoints_chat import create_chat_endpoints

logger = logging.getLogger(__name__)

# ============================================================================
# UTILITAIRES INTÉGRÉS
# ============================================================================

# Mémoire de conversation
conversation_memory: Dict[str, deque] = {}


def add_to_conversation_memory(
    session_id: str, message: Dict[str, Any], max_size: int = 50
):
    """Ajoute un message à la mémoire de conversation"""
    if session_id not in conversation_memory:
        conversation_memory[session_id] = deque(maxlen=max_size)

    conversation_memory[session_id].append(
        {**message, "timestamp": datetime.now().isoformat()}
    )


# Collecteur de métriques
class MetricsCollector:
    """Collecteur simple de métriques"""

    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "start_time": datetime.now().isoformat(),
        }

    def increment(self, metric: str, value: int = 1):
        """Incrémente une métrique"""
        if metric in self.metrics:
            self.metrics[metric] += value

    def get_metrics(self) -> Dict[str, Any]:
        """Retourne toutes les métriques"""
        return self.metrics.copy()


metrics_collector = MetricsCollector()


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
            "version": "4.1.0-modular",
            "timestamp": time.time(),
            "architecture": "modular-endpoints",
            "modules": ["health", "diagnostic", "chat", "utils"],
            "services_count": len(_services),
            "services_list": list(_services.keys()),
        }

    @router.get(f"{BASE_PATH}/deployment-test")
    async def deployment_test():
        """Endpoint de test simple pour confirmer le déploiement"""
        return {
            "message": "ARCHITECTURE MODULAIRE - Endpoints séparés",
            "version": "4.1.0-modular",
            "timestamp": time.time(),
            "architecture": "modular-endpoints",
            "files": [
                "endpoints.py",
                "endpoints_utils.py",
                "endpoints_health.py",
                "endpoints_diagnostic.py",
                "endpoints_chat.py",
            ],
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

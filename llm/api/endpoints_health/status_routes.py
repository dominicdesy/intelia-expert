# -*- coding: utf-8 -*-
"""
api/endpoints_health/status_routes.py - Status endpoints for various services
"""

import time
import logging
from utils.types import Callable
from fastapi import APIRouter

from config.config import BASE_PATH
from utils.utilities import safe_get_attribute, safe_dict_get
from utils.imports_and_dependencies import get_full_status_report

# CORRECTION: Import depuis utils pour éviter l'import circulaire
from ..utils import safe_serialize_for_json, conversation_memory

logger = logging.getLogger(__name__)


def create_status_routes(get_service: Callable) -> APIRouter:
    """Creates status check routes for various services"""

    router = APIRouter()

    # ========================================================================
    # STATUS ENDPOINTS
    # ========================================================================

    @router.get(f"{BASE_PATH}/status/rag")
    async def rag_status():
        """Statut détaillé du RAG Engine"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {
                    "initialized": False,
                    "error": "Health monitor non disponible",
                    "timestamp": time.time(),
                }

            rag_engine = health_monitor.get_service("rag_engine_enhanced")
            if not rag_engine:
                return {
                    "initialized": False,
                    "degraded_mode": True,
                    "error": "RAG Engine non disponible",
                    "timestamp": time.time(),
                }

            try:
                status = rag_engine.get_status()
                safe_status = safe_serialize_for_json(status)
            except Exception as e:
                logger.error(f"Erreur récupération statut RAG: {e}")
                safe_status = {
                    "error": f"status_error: {str(e)}",
                    "error_type": type(e).__name__,
                }

            return {
                "initialized": safe_get_attribute(rag_engine, "is_initialized", False),
                "degraded_mode": safe_get_attribute(rag_engine, "degraded_mode", False),
                "approach": safe_dict_get(safe_status, "approach", "unknown"),
                "optimizations": safe_dict_get(safe_status, "optimizations", {}),
                "langsmith": safe_dict_get(safe_status, "langsmith", {}),
                "intelligent_rrf": safe_dict_get(safe_status, "intelligent_rrf", {}),
                "optimization_stats": safe_dict_get(
                    safe_status, "optimization_stats", {}
                ),
                "weaviate_connected": bool(
                    safe_get_attribute(rag_engine, "weaviate_client")
                ),
                "timestamp": time.time(),
                "serialization_version": "optimized_cached",
            }

        except Exception as e:
            logger.error(f"Erreur RAG status: {e}")
            return {
                "initialized": False,
                "degraded_mode": True,
                "error": str(e),
                "timestamp": time.time(),
                "serialization_version": "optimized_cached",
            }

    @router.get(f"{BASE_PATH}/status/dependencies")
    async def dependencies_status():
        """Statut détaillé des dépendances"""
        try:
            status = get_full_status_report()
            return safe_serialize_for_json(status)
        except Exception as e:
            return {"error": str(e), "serialization_version": "optimized_cached"}

    @router.get(f"{BASE_PATH}/status/cache")
    async def cache_status():
        """Statut détaillé du cache Redis"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {
                    "enabled": False,
                    "available": False,
                    "initialized": False,
                    "error": "Health monitor non disponible",
                    "timestamp": time.time(),
                    "serialization_version": "optimized_cached",
                }

            cache_core = health_monitor.get_service("cache_core")
            if not cache_core:
                return {
                    "enabled": False,
                    "available": False,
                    "initialized": False,
                    "error": "Cache Core non trouvé",
                    "timestamp": time.time(),
                    "serialization_version": "optimized_cached",
                }

            cache_stats = {}
            try:
                if hasattr(cache_core, "get_cache_stats"):
                    cache_stats = await cache_core.get_cache_stats()
                elif hasattr(cache_core, "get_stats"):
                    cache_stats = cache_core.get_stats()

                cache_stats = safe_serialize_for_json(cache_stats)
            except Exception as e:
                cache_stats = {"stats_error": str(e)}

            enabled = safe_get_attribute(cache_core, "enabled", False)
            initialized = safe_get_attribute(cache_core, "initialized", False)

            # Récupération sécurisée des stats de cache de sérialisation
            try:
                from ..endpoints import _get_serialization_strategy

                serialization_cache_info = (
                    _get_serialization_strategy.cache_info()._asdict()
                )
            except (ImportError, AttributeError) as e:
                logger.debug(
                    f"Impossible de récupérer les stats de cache de sérialisation: {e}"
                )
                serialization_cache_info = {"unavailable": True}

            return {
                "enabled": enabled,
                "available": enabled and initialized,
                "initialized": initialized,
                "stats": cache_stats,
                "timestamp": time.time(),
                "serialization_version": "optimized_cached",
                "memory_stats": conversation_memory.get("stats", {}),
                "performance": {"serialization_cache_hits": serialization_cache_info},
            }

        except Exception as e:
            logger.error(f"Erreur cache status: {e}")
            return {
                "enabled": False,
                "available": False,
                "initialized": False,
                "error": str(e),
                "timestamp": time.time(),
                "serialization_version": "optimized_cached",
            }

    # ========================================================================
    # ENDPOINTS LEGACY
    # ========================================================================

    @router.get(f"{BASE_PATH}/rag/status")
    async def rag_status_legacy():
        """CORRECTION: Endpoint manquant qui causait 404 dans les logs"""
        try:
            return await rag_status()
        except Exception as e:
            logger.error(f"Erreur endpoint legacy rag/status: {e}")
            return {
                "error": "Endpoint legacy failed",
                "redirect_to": f"{BASE_PATH}/status/rag",
                "timestamp": time.time(),
            }

    return router

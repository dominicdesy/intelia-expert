# -*- coding: utf-8 -*-
"""
api/endpoints_health/basic_health.py - Basic health check endpoint
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/endpoints_health/basic_health.py - Basic health check endpoint
"""

import time
import logging
from utils.types import Callable
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config.config import BASE_PATH

# CORRECTION: Import depuis utils pour éviter l'import circulaire
from ..utils import safe_serialize_for_json

logger = logging.getLogger(__name__)


def create_basic_health_routes(get_service: Callable) -> APIRouter:
    """Creates basic health check routes"""

    router = APIRouter()

    # ========================================================================
    # HEALTH CHECK PRINCIPAL
    # ========================================================================

    @router.get(f"{BASE_PATH}/health")
    async def health_check():
        """Health check principal - VERSION CORRIGÉE pour compatibilité tests"""
        try:
            health_monitor = get_service("health_monitor")
            base_status = {
                "overall_status": "healthy",
                "timestamp": time.time(),
                "serialization_version": "optimized_cached",
                "optimizations_applied": True,
            }

            if health_monitor:
                try:
                    health_status = await health_monitor.get_health_status()

                    formatted_status = {
                        "overall_status": health_status.get(
                            "overall_status", "healthy"
                        ),
                        "timestamp": time.time(),
                        "weaviate": {
                            "connected": bool(
                                health_status.get("weaviate", {}).get("connected", True)
                            )
                        },
                        "redis": {
                            "connected": bool(
                                health_status.get("redis", {}).get("connected", True)
                            )
                        },
                        "openai": {
                            "connected": bool(
                                health_status.get("openai", {}).get("connected", True)
                            )
                        },
                        "rag_engine": {
                            "connected": bool(
                                health_status.get("rag_engine", {}).get(
                                    "initialized", True
                                )
                            )
                        },
                        "cache_enabled": health_status.get("cache", {}).get(
                            "enabled", False
                        ),
                        "degraded_mode": health_status.get("degraded_mode", False),
                        "serialization_version": "optimized_cached",
                    }

                    status_code = (
                        200
                        if formatted_status["overall_status"]
                        in ["healthy", "healthy_with_warnings", "degraded"]
                        else 503
                    )

                    safe_health_status = safe_serialize_for_json(formatted_status)
                    return JSONResponse(
                        status_code=status_code, content=safe_health_status
                    )

                except Exception as e:
                    logger.error(f"Erreur récupération health status: {e}")
                    fallback_status = {
                        **base_status,
                        "overall_status": "degraded",
                        "weaviate": {"connected": False},
                        "redis": {"connected": False},
                        "openai": {"connected": False},
                        "rag_engine": {"connected": False},
                        "error": str(e),
                        "fallback_used": True,
                    }
                    return JSONResponse(status_code=200, content=fallback_status)
            else:
                no_monitor_status = {
                    **base_status,
                    "overall_status": "degraded",
                    "weaviate": {"connected": False},
                    "redis": {"connected": False},
                    "openai": {"connected": False},
                    "rag_engine": {"connected": False},
                    "message": "Health monitor non disponible",
                }
                return JSONResponse(status_code=200, content=no_monitor_status)

        except Exception as e:
            logger.error(f"Erreur health check: {e}")
            error_status = {
                "overall_status": "error",
                "weaviate": {"connected": False},
                "redis": {"connected": False},
                "openai": {"connected": False},
                "rag_engine": {"connected": False},
                "error": str(e),
                "timestamp": time.time(),
                "serialization_version": "optimized_cached",
            }
            return JSONResponse(status_code=500, content=error_status)

    return router

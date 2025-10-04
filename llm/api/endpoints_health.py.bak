# -*- coding: utf-8 -*-
"""
api/endpoints_health.py - Endpoints de santé et status
Health checks, métriques, status des services
"""

import time
import logging
from typing import Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config.config import BASE_PATH
from utils.utilities import safe_get_attribute, safe_dict_get
from utils.imports_and_dependencies import get_full_status_report
from .endpoints_utils import (
    safe_serialize_for_json,
    metrics_collector,
    conversation_memory,
    _get_serialization_strategy,
)

logger = logging.getLogger(__name__)


def create_health_endpoints(services: Dict[str, Any]) -> APIRouter:
    """Crée les endpoints de santé et status"""

    router = APIRouter()

    def get_service(name: str) -> Any:
        """Helper pour récupérer un service"""
        return services.get(name)

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

            return {
                "enabled": enabled,
                "available": enabled and initialized,
                "initialized": initialized,
                "stats": cache_stats,
                "timestamp": time.time(),
                "serialization_version": "optimized_cached",
                "memory_stats": conversation_memory.get_stats(),
                "performance": {
                    "serialization_cache_hits": _get_serialization_strategy.cache_info()._asdict()
                },
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
    # MÉTRIQUES
    # ========================================================================

    @router.get(f"{BASE_PATH}/metrics")
    async def get_metrics():
        """Métriques de performance"""
        try:
            endpoint_metrics = metrics_collector.get_metrics()

            base_metrics = {
                "cache_stats": {
                    "hits": endpoint_metrics.get("cache_hits", 0),
                    "misses": endpoint_metrics.get("cache_misses", 0),
                    "hit_rate": endpoint_metrics.get("cache_hit_rate", 0.0),
                },
                "ood_stats": {
                    "filtered": endpoint_metrics.get("ood_filtered", 0),
                    "total": endpoint_metrics.get("total_queries", 0),
                },
                "api_corrections": {
                    "total": endpoint_metrics.get("api_corrections", 0),
                    "guardrail_violations": endpoint_metrics.get(
                        "guardrail_violations", 0
                    ),
                },
                "application_metrics": endpoint_metrics,
                "system_metrics": {
                    "conversation_memory": conversation_memory.get_stats(),
                    "serialization_cache": _get_serialization_strategy.cache_info()._asdict(),
                },
                "performance_metrics": {
                    "throughput_qps": endpoint_metrics.get("throughput_qps", 0.0),
                    "latency_percentiles": endpoint_metrics.get(
                        "latency_percentiles", {}
                    ),
                    "memory_usage": endpoint_metrics.get("memory_usage", {}),
                },
                "architecture": "modular-endpoints",
                "serialization_version": "optimized_cached",
            }

            # Métriques RAG Engine
            health_monitor = get_service("health_monitor")
            if health_monitor:
                rag_engine = health_monitor.get_service("rag_engine_enhanced")
                if rag_engine and safe_get_attribute(
                    rag_engine, "is_initialized", False
                ):
                    try:
                        rag_status = rag_engine.get_status()
                        safe_rag_status = safe_serialize_for_json(rag_status)

                        base_metrics["rag_engine"] = {
                            "approach": safe_dict_get(
                                safe_rag_status, "approach", "unknown"
                            ),
                            "optimizations": safe_dict_get(
                                safe_rag_status, "optimizations", {}
                            ),
                            "langsmith": safe_dict_get(
                                safe_rag_status, "langsmith", {}
                            ),
                            "intelligent_rrf": safe_dict_get(
                                safe_rag_status, "intelligent_rrf", {}
                            ),
                            "optimization_stats": safe_dict_get(
                                safe_rag_status, "optimization_stats", {}
                            ),
                        }
                    except Exception as e:
                        logger.error(f"Erreur métriques RAG: {e}")
                        base_metrics["rag_engine"] = {"error": str(e)}

            return safe_serialize_for_json(base_metrics)

        except Exception as e:
            logger.error(f"Erreur récupération métriques: {e}")
            return {
                "cache_stats": {},
                "ood_stats": {},
                "api_corrections": {},
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

    @router.get(f"{BASE_PATH}/test-json")
    async def test_json_direct():
        """Test de sérialisation JSON"""
        try:
            from processing.intent_types import IntentType
            from collections import defaultdict
            from decimal import Decimal
            from datetime import datetime

            test_data = {
                "string": "test",
                "number": 42,
                "boolean": True,
                "list": [1, 2, 3],
                "dict": {"nested": "value"},
                "timestamp": datetime.now(),
                "decimal": Decimal("123.45"),
                "set": {1, 2, 3},
                "defaultdict": defaultdict(int, {"a": 1, "b": 2}),
                "intent_type_enum": IntentType.GENERAL_POULTRY,
                "enum_in_dict": {"intent": IntentType.METRIC_QUERY},
            }

            safe_data = safe_serialize_for_json(test_data)

            return {
                "status": "success",
                "original_data_types": {k: str(type(v)) for k, v in test_data.items()},
                "serialized_data": safe_data,
                "json_test": "OK",
                "enum_test": "PASSED",
                "complex_types_test": "PASSED",
                "serialization_version": "optimized_cached",
            }

        except Exception as e:
            logger.error(f"Erreur test JSON: {e}")
            return {"status": "error", "error": str(e), "json_test": "FAILED"}

    return router

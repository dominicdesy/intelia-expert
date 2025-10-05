# -*- coding: utf-8 -*-
"""
api/endpoints_health/metrics_routes.py - Metrics and testing endpoints
"""

import time
import logging
from utils.types import Callable
from fastapi import APIRouter

from config.config import BASE_PATH
from utils.utilities import safe_get_attribute, safe_dict_get

# CORRECTION: Import depuis utils pour éviter l'import circulaire
from ..utils import safe_serialize_for_json, metrics_collector

logger = logging.getLogger(__name__)


def create_metrics_routes(get_service: Callable) -> APIRouter:
    """Creates metrics and testing routes"""

    router = APIRouter()

    # ========================================================================
    # MÉTRIQUES
    # ========================================================================

    @router.get(f"{BASE_PATH}/metrics")
    async def get_metrics():
        """Métriques de performance et monitoring"""
        try:
            # Métriques existantes
            endpoint_metrics = metrics_collector.get_metrics()

            # NOUVEAU: Métriques du système de monitoring
            from monitoring.metrics import get_metrics_collector

            monitoring_metrics = get_metrics_collector().get_stats()

            # NOUVEAU: Métriques Multi-LLM Router
            llm_router_stats = {}
            try:
                from generation.llm_router import get_llm_router

                llm_router = get_llm_router()
                llm_router_stats = llm_router.get_stats()
            except Exception as e:
                logger.debug(f"LLM Router stats unavailable: {e}")
                llm_router_stats = {"unavailable": True}

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
                    "conversation_memory": {},
                    "serialization_cache": serialization_cache_info,
                },
                "performance_metrics": {
                    "throughput_qps": endpoint_metrics.get("throughput_qps", 0.0),
                    "latency_percentiles": endpoint_metrics.get(
                        "latency_percentiles", {}
                    ),
                    "memory_usage": endpoint_metrics.get("memory_usage", {}),
                },
                # NOUVEAU: Métriques de monitoring
                "monitoring": monitoring_metrics,
                # NOUVEAU: Métriques Multi-LLM Router
                "llm_router": llm_router_stats,
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

                        # NOUVEAU: Métriques Cohere Reranker
                        if "reranker_stats" in safe_rag_status:
                            base_metrics["rag_engine"]["cohere_reranker"] = (
                                safe_dict_get(safe_rag_status, "reranker_stats", {})
                            )
                        else:
                            # Essayer de récupérer directement depuis weaviate_core
                            weaviate_core = getattr(rag_engine, "weaviate_core", None)
                            if weaviate_core and hasattr(weaviate_core, "reranker"):
                                reranker = weaviate_core.reranker
                                if reranker:
                                    base_metrics["rag_engine"]["cohere_reranker"] = (
                                        safe_serialize_for_json(reranker.get_stats())
                                    )

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
    # TESTING ENDPOINTS
    # ========================================================================

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

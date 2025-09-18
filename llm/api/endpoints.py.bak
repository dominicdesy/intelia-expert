# -*- coding: utf-8 -*-
"""
api/endpoints.py - Module des endpoints API
VERSION CORRIGÉE - Cache status avec gestion robuste des erreurs
"""

import time
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional
from collections import OrderedDict

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

# Imports modulaires
from config.config import (
    BASE_PATH,
    MAX_CONVERSATION_CONTEXT,
    TENANT_TTL,
    MAX_TENANTS,
    STREAM_CHUNK_LEN,
    ENABLE_METRICS_LOGGING,
)
from utils.utilities import (
    safe_serialize_for_json,
    safe_get_attribute,
    safe_dict_get,
    sse_event,
    smart_chunk_text,
    get_out_of_domain_message,
    get_aviculture_response,
    MetricsCollector,
    detect_language_enhanced,
)

from utils.imports_and_dependencies import get_full_status_report

MAX_REQUEST_SIZE = 8000  # Garde cette constante locale

logger = logging.getLogger(__name__)

# ============================================================================
# GESTION MÉMOIRE TENANT (Version modulaire)
# ============================================================================


class TenantMemory(OrderedDict):
    """Cache LRU avec TTL pour la mémoire de conversation - Version modulaire"""

    def __init__(self):
        super().__init__()
        self.tenant_ttl = TENANT_TTL
        self.max_tenants = MAX_TENANTS

    def set(self, tenant_id: str, item: list):
        if not tenant_id or not isinstance(item, list):
            logger.warning(
                f"Paramètres invalides pour TenantMemory.set: {tenant_id}, {type(item)}"
            )
            return

        now = time.time()
        self[tenant_id] = {"data": item, "ts": now, "last_query": ""}
        self.move_to_end(tenant_id)

        # Purge TTL
        try:
            expired_keys = [
                k for k, v in self.items() if now - v.get("ts", 0) > self.tenant_ttl
            ]
            for k in expired_keys:
                del self[k]
                logger.debug(f"Tenant {k} expiré (TTL)")
        except Exception as e:
            logger.warning(f"Erreur purge TTL: {e}")

        # Purge LRU
        try:
            while len(self) > self.max_tenants:
                oldest_tenant, _ = self.popitem(last=False)
                logger.debug(f"Tenant {oldest_tenant} purgé (LRU)")
        except Exception as e:
            logger.warning(f"Erreur purge LRU: {e}")

    def get(self, tenant_id: str, default=None):
        if not tenant_id or tenant_id not in self:
            return default

        try:
            now = time.time()
            if now - self[tenant_id].get("ts", 0) > self.tenant_ttl:
                del self[tenant_id]
                return default

            self[tenant_id]["ts"] = now
            self.move_to_end(tenant_id)
            return self[tenant_id]
        except Exception as e:
            logger.warning(f"Erreur récupération tenant {tenant_id}: {e}")
            return default

    def update_last_query(self, tenant_id: str, query: str):
        """Met à jour la dernière requête pour un tenant"""
        if tenant_id in self and isinstance(query, str):
            try:
                self[tenant_id]["last_query"] = query[:500]
            except Exception as e:
                logger.warning(f"Erreur mise à jour last_query: {e}")


# Instance globale
conversation_memory = TenantMemory()


def add_to_conversation_memory(
    tenant_id: str, question: str, answer: str, source: str = "rag_enhanced"
):
    """Ajoute un échange à la mémoire de conversation avec validation"""
    if not tenant_id or not question or not answer:
        logger.warning("Paramètres invalides pour add_to_conversation_memory")
        return

    try:
        tenant_data = conversation_memory.get(tenant_id, {"data": []})
        history = tenant_data.get("data", [])

        history.append(
            {
                "question": question[:1000],
                "answer": answer[:2000],
                "timestamp": time.time(),
                "answer_source": source,
            }
        )

        if len(history) > MAX_CONVERSATION_CONTEXT:
            history = history[-MAX_CONVERSATION_CONTEXT:]

        conversation_memory.set(tenant_id, history)
        conversation_memory.update_last_query(tenant_id, question)
    except Exception as e:
        logger.error(f"Erreur ajout conversation memory: {e}")


# ============================================================================
# COLLECTEUR DE MÉTRIQUES POUR ENDPOINTS
# ============================================================================


class EndpointMetricsCollector(MetricsCollector):
    """Collecteur de métriques spécialisé pour les endpoints"""

    def __init__(self):
        super().__init__()
        self.endpoint_metrics = {
            "total_queries": 0,
            "rag_enhanced_queries": 0,
            "agent_queries": 0,
            "simple_queries": 0,
            "complex_queries": 0,
            "rag_standard_queries": 0,
            "ood_filtered": 0,
            "fallback_queries": 0,
            "verified_responses": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "semantic_cache_hits": 0,
            "fallback_cache_hits": 0,
            "hybrid_searches": 0,
            "guardrail_violations": 0,
            "api_corrections": 0,
            "errors": 0,
            "langsmith_traces": 0,
            "langsmith_errors": 0,
            "hallucination_alerts": 0,
            "intelligent_rrf_queries": 0,
            "genetic_boosts_applied": 0,
            "rrf_learning_updates": 0,
            "avg_processing_time": 0.0,
            "avg_confidence": 0.0,
        }
        self.recent_processing_times = []
        self.recent_confidences = []
        self.latency_percentiles = {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        self.max_recent_samples = 100

    def record_query(
        self, result, source_type: str = "unknown", endpoint_time: float = 0.0
    ):
        """Enregistre les métriques avec support LangSmith et RRF - VERSION SÉCURISÉE"""
        if not ENABLE_METRICS_LOGGING:
            return

        try:
            self.endpoint_metrics["total_queries"] += 1

            # Gestion selon le type de source
            if source_type == "rag_enhanced":
                self.endpoint_metrics["rag_enhanced_queries"] += 1
            elif source_type == "agent_rag":
                self.endpoint_metrics["agent_queries"] += 1
            elif source_type == "error":
                self.endpoint_metrics["errors"] += 1

            # Traitement selon le type de résultat - VERSION SÉCURISÉE
            if result and hasattr(result, "source"):
                try:
                    source_obj = safe_get_attribute(result, "source")
                    if source_obj:
                        source_value = safe_get_attribute(
                            source_obj, "value", str(source_obj)
                        )
                        source_value_str = str(source_value).lower()

                        if "rag" in source_value_str:
                            self.endpoint_metrics["rag_standard_queries"] += 1
                        elif "ood" in source_value_str:
                            self.endpoint_metrics["ood_filtered"] += 1
                        else:
                            self.endpoint_metrics["fallback_queries"] += 1
                except Exception as e:
                    logger.debug(f"Erreur traitement source metrics: {e}")
                    self.endpoint_metrics["fallback_queries"] += 1

            # Métriques LangSmith et RRF avec validation
            metadata = safe_get_attribute(result, "metadata")
            if metadata and isinstance(metadata, dict):
                try:
                    # LangSmith
                    langsmith_data = safe_dict_get(metadata, "langsmith", {})
                    if safe_dict_get(langsmith_data, "traced", False):
                        self.endpoint_metrics["langsmith_traces"] += 1

                    if safe_dict_get(metadata, "alerts_aviculture"):
                        self.endpoint_metrics["hallucination_alerts"] += 1

                    # RRF Intelligent
                    rrf_data = safe_dict_get(metadata, "intelligent_rrf", {})
                    if safe_dict_get(rrf_data, "used", False):
                        self.endpoint_metrics["intelligent_rrf_queries"] += 1

                    opt_stats = safe_dict_get(metadata, "optimization_stats", {})
                    if isinstance(opt_stats, dict):
                        self.endpoint_metrics["cache_hits"] += int(
                            safe_dict_get(opt_stats, "cache_hits", 0)
                        )
                        self.endpoint_metrics["cache_misses"] += int(
                            safe_dict_get(opt_stats, "cache_misses", 0)
                        )
                        self.endpoint_metrics["semantic_cache_hits"] += int(
                            safe_dict_get(opt_stats, "semantic_cache_hits", 0)
                        )
                        self.endpoint_metrics["hybrid_searches"] += int(
                            safe_dict_get(opt_stats, "hybrid_searches", 0)
                        )
                        self.endpoint_metrics["genetic_boosts_applied"] += int(
                            safe_dict_get(opt_stats, "genetic_boosts_applied", 0)
                        )
                        self.endpoint_metrics["rrf_learning_updates"] += int(
                            safe_dict_get(opt_stats, "rrf_learning_updates", 0)
                        )

                except Exception as e:
                    logger.debug(f"Erreur traitement métriques metadata: {e}")

            # Calcul des métriques temporelles
            processing_time = (
                endpoint_time
                if endpoint_time > 0
                else safe_get_attribute(result, "processing_time", 0)
            )

            if processing_time > 0:
                self.recent_processing_times.append(float(processing_time))
                if len(self.recent_processing_times) > self.max_recent_samples:
                    self.recent_processing_times.pop(0)

                # Calcul de la moyenne
                if self.recent_processing_times:
                    self.endpoint_metrics["avg_processing_time"] = sum(
                        self.recent_processing_times
                    ) / len(self.recent_processing_times)

            # Confiance
            confidence = safe_get_attribute(result, "confidence", 0)
            if confidence > 0:
                self.recent_confidences.append(float(confidence))
                if len(self.recent_confidences) > self.max_recent_samples:
                    self.recent_confidences.pop(0)

                if self.recent_confidences:
                    self.endpoint_metrics["avg_confidence"] = sum(
                        self.recent_confidences
                    ) / len(self.recent_confidences)

        except Exception as e:
            logger.warning(f"Erreur enregistrement métriques: {e}")
            self.endpoint_metrics["errors"] = self.endpoint_metrics.get("errors", 0) + 1

    def get_metrics(self) -> Dict:
        """Retourne les métriques enrichies avec protection contre les erreurs"""
        try:
            total_queries = max(1, self.endpoint_metrics["total_queries"])
            total_cache_requests = max(
                1,
                self.endpoint_metrics["cache_hits"]
                + self.endpoint_metrics["cache_misses"],
            )

            return {
                **self.endpoint_metrics,
                "success_rate": (
                    (
                        self.endpoint_metrics["rag_enhanced_queries"]
                        + self.endpoint_metrics["verified_responses"]
                        + self.endpoint_metrics["agent_queries"]
                    )
                    / total_queries
                ),
                "enhanced_rag_usage_rate": self.endpoint_metrics["rag_enhanced_queries"]
                / total_queries,
                "cache_hit_rate": self.endpoint_metrics["cache_hits"]
                / total_cache_requests,
                "semantic_cache_hit_rate": self.endpoint_metrics["semantic_cache_hits"]
                / total_cache_requests,
                "error_rate": self.endpoint_metrics["errors"] / total_queries,
                "latency_percentiles": self.latency_percentiles,
                "langsmith_usage_rate": self.endpoint_metrics["langsmith_traces"]
                / total_queries,
                "rrf_intelligent_usage_rate": self.endpoint_metrics[
                    "intelligent_rrf_queries"
                ]
                / total_queries,
                "hallucination_alert_rate": self.endpoint_metrics[
                    "hallucination_alerts"
                ]
                / total_queries,
            }
        except Exception as e:
            logger.error(f"Erreur calcul métriques: {e}")
            return self.endpoint_metrics


# Instance globale
metrics_collector = EndpointMetricsCollector()

# ============================================================================
# CRÉATION DU ROUTER AVEC SERVICES - VERSION CORRIGÉE
# ============================================================================


def create_router(services: Optional[Dict[str, Any]] = None) -> APIRouter:
    """Crée le router avec les services injectés"""

    router = APIRouter()

    # Services par défaut (seront injectés depuis main.py)
    _services = services or {}

    def get_service(name: str) -> Any:
        """Helper pour récupérer un service"""
        return _services.get(name)

    # ========================================================================
    # ENDPOINTS HEALTH CHECK
    # ========================================================================

    @router.get("/health")
    async def health_check():
        """Health check principal"""
        try:
            health_monitor = get_service("health_monitor")
            if health_monitor:
                health_status = await health_monitor.get_health_status()

                # Code de statut HTTP selon l'état
                if health_status["overall_status"] in [
                    "healthy",
                    "healthy_with_warnings",
                ]:
                    status_code = 200
                elif health_status["overall_status"] == "degraded":
                    status_code = 200
                else:
                    status_code = 503

                return JSONResponse(status_code=status_code, content=health_status)
            else:
                return JSONResponse(
                    status_code=200,
                    content={
                        "overall_status": "basic",
                        "timestamp": time.time(),
                        "message": "Health monitor non disponible",
                    },
                )

        except Exception as e:
            logger.error(f"Erreur health check: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "overall_status": "error",
                    "error": str(e),
                    "timestamp": time.time(),
                },
            )

    @router.get(f"{BASE_PATH}/status/dependencies")
    async def dependencies_status():
        """Statut détaillé des dépendances"""
        try:
            return get_full_status_report()
        except Exception as e:
            return {"error": str(e)}

    @router.get(f"{BASE_PATH}/status/rag")
    async def rag_status():
        """Statut détaillé du RAG Engine"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {"error": "Health monitor non disponible"}

            rag_engine = health_monitor.get_service("rag_engine_enhanced")
            if not rag_engine:
                return {
                    "initialized": False,
                    "error": "RAG Engine non disponible",
                    "timestamp": time.time(),
                }

            # Récupération sécurisée du statut
            try:
                status = rag_engine.get_status()
                safe_status = safe_serialize_for_json(status)
            except Exception as e:
                logger.error(f"Erreur récupération statut RAG: {e}")
                safe_status = {"error": f"status_error: {str(e)}"}

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
            }

        except Exception as e:
            logger.error(f"Erreur RAG status: {e}")
            return {"initialized": False, "error": str(e), "timestamp": time.time()}

    # CORRECTION PRINCIPALE: Endpoint cache status avec gestion robuste
    @router.get(f"{BASE_PATH}/status/cache")
    async def cache_status():
        """Statut détaillé du cache Redis - VERSION CORRIGÉE"""
        try:
            health_monitor = get_service("health_monitor")

            # NOUVELLE LOGIQUE: Plus de "Health monitor non disponible"
            if not health_monitor:
                return {
                    "enabled": False,
                    "initialized": False,
                    "available": False,
                    "error": "SystemHealthMonitor non accessible depuis les services",
                    "debug_info": {
                        "services_available": list(_services.keys()),
                        "health_monitor_in_services": "health_monitor" in _services,
                    },
                    "timestamp": time.time(),
                }

            # Tenter de récupérer le cache_core
            cache_core = health_monitor.get_service("cache_core")
            if not cache_core:
                # Diagnostic détaillé si cache_core absent
                all_services = (
                    health_monitor.get_all_services()
                    if hasattr(health_monitor, "get_all_services")
                    else {}
                )

                return {
                    "enabled": False,
                    "initialized": False,
                    "available": False,
                    "error": "Cache Core non trouvé dans les services du health monitor",
                    "debug_info": {
                        "health_monitor_services": list(all_services.keys()),
                        "cache_core_in_services": "cache_core" in all_services,
                        "services_count": len(all_services),
                    },
                    "timestamp": time.time(),
                }

            # Cache_core trouvé - analyser son état
            cache_enabled = safe_get_attribute(cache_core, "enabled", False)
            cache_initialized = safe_get_attribute(cache_core, "initialized", False)

            # Récupération sécurisée des statistiques
            cache_stats = {}
            cache_health = {}

            try:
                if hasattr(cache_core, "get_cache_stats"):
                    cache_stats = await cache_core.get_cache_stats()
                elif hasattr(cache_core, "get_stats"):
                    cache_stats = cache_core.get_stats()
            except Exception as stats_e:
                cache_stats = {"stats_error": str(stats_e)}

            try:
                if hasattr(cache_core, "get_health_status"):
                    cache_health = cache_core.get_health_status()
            except Exception as health_e:
                cache_health = {"health_error": str(health_e)}

            return {
                "enabled": cache_enabled,
                "initialized": cache_initialized,
                "available": True,
                "status": safe_dict_get(cache_health, "status", "unknown"),
                "stats": safe_serialize_for_json(cache_stats),
                "health": safe_serialize_for_json(cache_health),
                "debug_info": {
                    "cache_core_type": type(cache_core).__name__,
                    "cache_core_methods": [
                        method
                        for method in dir(cache_core)
                        if not method.startswith("_")
                        and callable(getattr(cache_core, method))
                    ][
                        :10
                    ],  # Limiter à 10 méthodes pour lisibilité
                    "has_client": hasattr(cache_core, "client"),
                    "client_available": getattr(cache_core, "client", None) is not None,
                    "has_config": hasattr(cache_core, "config"),
                },
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.error(f"Erreur cache status: {e}")
            return {
                "enabled": False,
                "initialized": False,
                "available": False,
                "error": f"Erreur lors de la vérification du statut cache: {str(e)}",
                "debug_info": {
                    "exception_type": type(e).__name__,
                    "services_available": list(_services.keys()),
                },
                "timestamp": time.time(),
            }

    @router.get(f"{BASE_PATH}/metrics")
    async def get_metrics():
        """Endpoint pour récupérer les métriques de performance enrichies"""
        try:
            base_metrics = {
                "application_metrics": metrics_collector.get_metrics(),
                "system_metrics": {
                    "conversation_memory": {
                        "tenants": len(conversation_memory),
                        "max_tenants": MAX_TENANTS,
                        "ttl_seconds": TENANT_TTL,
                    }
                },
            }

            # Métriques RAG Engine enrichies
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
                            "weaviate_capabilities": safe_dict_get(
                                safe_rag_status, "api_capabilities", {}
                            ),
                        }
                    except Exception as e:
                        logger.error(f"Erreur métriques RAG: {e}")
                        base_metrics["rag_engine"] = {"error": str(e)}

                # Cache stats externe - CORRECTION
                cache_core = health_monitor.get_service("cache_core")
                if cache_core:
                    try:
                        if hasattr(cache_core, "get_cache_stats"):
                            cache_stats = await cache_core.get_cache_stats()
                        elif hasattr(cache_core, "get_stats"):
                            cache_stats = cache_core.get_stats()
                        else:
                            cache_stats = {
                                "enabled": getattr(cache_core, "enabled", False),
                                "initialized": getattr(
                                    cache_core, "initialized", False
                                ),
                                "no_stats_method": True,
                            }

                        base_metrics["cache"] = safe_serialize_for_json(cache_stats)
                    except Exception as e:
                        logger.error(f"Erreur métriques cache: {e}")
                        base_metrics["cache"] = {"error": str(e)}

            return base_metrics

        except Exception as e:
            logger.error(f"Erreur récupération métriques: {e}")
            return {"error": str(e), "timestamp": time.time()}

    # ========================================================================
    # ENDPOINT CHAT PRINCIPAL
    # ========================================================================

    @router.post(f"{BASE_PATH}/chat")
    async def chat(request: Request):
        """Chat endpoint avec vraies réponses aviculture - VERSION MODULAIRE"""
        total_start_time = time.time()

        try:
            # Validation de la requête
            try:
                body = await request.json()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"JSON invalide: {e}")

            message = body.get("message", "").strip()
            language = body.get("language", "").strip()
            tenant_id = body.get("tenant_id", str(uuid.uuid4())[:8])

            # Validations
            if not message:
                raise HTTPException(status_code=400, detail="Message vide")

            if len(message) > MAX_REQUEST_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Message trop long (max {MAX_REQUEST_SIZE})",
                )

            # Détection de langue si non fournie
            if not language:
                language = detect_language_enhanced(message)

            # Validation tenant_id
            if not tenant_id or len(tenant_id) > 50:
                tenant_id = str(uuid.uuid4())[:8]

            # Logique de réponse avec services
            rag_result = None
            use_fallback = False
            fallback_reason = ""

            # Essayer le RAG Engine si disponible
            health_monitor = get_service("health_monitor")
            if health_monitor:
                rag_engine = health_monitor.get_service("rag_engine_enhanced")

                if rag_engine and safe_get_attribute(
                    rag_engine, "is_initialized", False
                ):
                    try:
                        # Essayer generate_response en premier
                        if hasattr(rag_engine, "generate_response"):
                            try:
                                rag_result = await rag_engine.generate_response(
                                    query=message,
                                    tenant_id=tenant_id,
                                    language=language,
                                )
                                logger.info("RAG generate_response réussi")

                            except Exception as generate_error:
                                logger.warning(
                                    f"generate_response échoué: {generate_error}"
                                )
                                use_fallback = True
                                fallback_reason = (
                                    f"generate_response_failed: {str(generate_error)}"
                                )
                        else:
                            use_fallback = True
                            fallback_reason = "generate_response_not_available"

                    except Exception as e:
                        logger.error(f"Erreur générale RAG: {e}")
                        use_fallback = True
                        fallback_reason = f"rag_general_error: {str(e)}"
                else:
                    use_fallback = True
                    fallback_reason = "rag_not_initialized"
            else:
                use_fallback = True
                fallback_reason = "health_monitor_unavailable"

            # Utiliser réponses aviculture au lieu de OOD
            if use_fallback or not rag_result:
                logger.info(
                    f"Utilisation fallback aviculture - Raison: {fallback_reason}"
                )

                # Générer une vraie réponse aviculture
                aviculture_response = get_aviculture_response(message, language)

                # Créer un objet résultat simulé
                class FallbackResult:
                    def __init__(self, answer, reason):
                        self.answer = answer
                        self.source = "aviculture_fallback"
                        self.confidence = 0.8
                        self.processing_time = time.time() - total_start_time
                        self.metadata = {
                            "fallback_used": True,
                            "fallback_reason": reason,
                            "source_type": "integrated_knowledge",
                        }
                        self.context_docs = []

                rag_result = FallbackResult(aviculture_response, fallback_reason)

            # Enregistrer métriques
            total_processing_time = time.time() - total_start_time
            metrics_collector.record_query(
                rag_result, "rag_enhanced", total_processing_time
            )

            # Streaming de la réponse
            async def generate_response():
                try:
                    # Informations de début
                    metadata = safe_get_attribute(rag_result, "metadata", {}) or {}
                    source = safe_get_attribute(rag_result, "source", "unknown")
                    confidence = safe_get_attribute(rag_result, "confidence", 0.5)
                    processing_time = safe_get_attribute(
                        rag_result, "processing_time", 0
                    )

                    # Convertir source enum si nécessaire
                    if hasattr(source, "value"):
                        source = source.value
                    else:
                        source = str(source)

                    yield sse_event(
                        {
                            "type": "start",
                            "source": source,
                            "confidence": float(confidence),
                            "processing_time": float(processing_time),
                            "fallback_used": safe_dict_get(
                                metadata, "fallback_used", False
                            ),
                        }
                    )

                    # Contenu de la réponse
                    answer = safe_get_attribute(rag_result, "answer", "")
                    if not answer:
                        # Essayer d'autres attributs possibles
                        answer = safe_get_attribute(rag_result, "response", "")
                        if not answer:
                            answer = safe_get_attribute(rag_result, "text", "")
                            if not answer:
                                answer = get_aviculture_response(message, language)

                    if answer:
                        chunks = smart_chunk_text(str(answer), STREAM_CHUNK_LEN)

                        for i, chunk in enumerate(chunks):
                            yield sse_event(
                                {"type": "chunk", "content": chunk, "chunk_index": i}
                            )
                            await asyncio.sleep(0.01)

                    # Informations finales
                    context_docs = safe_get_attribute(rag_result, "context_docs", [])
                    if not isinstance(context_docs, list):
                        context_docs = []

                    yield sse_event(
                        {
                            "type": "end",
                            "total_time": total_processing_time,
                            "confidence": float(confidence),
                            "documents_used": len(context_docs),
                            "source": source,
                        }
                    )

                    # Enregistrer en mémoire si tout est OK
                    if answer and source:
                        add_to_conversation_memory(
                            tenant_id, message, str(answer), "rag_enhanced"
                        )

                except Exception as e:
                    logger.error(f"Erreur streaming: {e}")
                    yield sse_event({"type": "error", "message": str(e)})

            return StreamingResponse(generate_response(), media_type="text/plain")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur chat endpoint: {e}")
            metrics_collector.record_query(
                {"source": "error"}, "error", time.time() - total_start_time
            )
            return JSONResponse(
                status_code=500, content={"error": f"Erreur traitement: {str(e)}"}
            )

    # ========================================================================
    # ENDPOINT OOD
    # ========================================================================

    @router.post(f"{BASE_PATH}/ood")
    async def ood_endpoint(request: Request):
        """Point de terminaison pour messages hors domaine"""
        try:
            body = await request.json()
            language = body.get("language", "fr")
            message = get_out_of_domain_message(language)

            async def ood_response():
                yield sse_event({"type": "start", "reason": "out_of_domain"})

                chunks = smart_chunk_text(message, STREAM_CHUNK_LEN)
                for chunk in chunks:
                    yield sse_event({"type": "chunk", "content": chunk})
                    await asyncio.sleep(0.05)

                yield sse_event({"type": "end", "confidence": 1.0})

            return StreamingResponse(ood_response(), media_type="text/plain")

        except Exception as e:
            logger.error(f"Erreur OOD endpoint: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    return router


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "create_router",
    "TenantMemory",
    "EndpointMetricsCollector",
    "add_to_conversation_memory",
    "conversation_memory",
    "metrics_collector",
]

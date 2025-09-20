# -*- coding: utf-8 -*-
"""
api/endpoints_utils.py - Utilitaires partagés pour les endpoints
Sérialisation, métriques, mémoire de conversation
"""

import time
import logging
from typing import Dict, Any
from collections import OrderedDict, defaultdict
from functools import lru_cache
from decimal import Decimal
from enum import Enum

from config.config import (
    TENANT_TTL,
    MAX_TENANTS,
    MAX_CONVERSATION_CONTEXT,
    ENABLE_METRICS_LOGGING,
)
from utils.utilities import MetricsCollector, safe_get_attribute

logger = logging.getLogger(__name__)

# ============================================================================
# SÉRIALISATION OPTIMISÉE
# ============================================================================


@lru_cache(maxsize=1000)
def _get_serialization_strategy(obj_type: type) -> str:
    """Cache des stratégies de sérialisation par type"""
    if issubclass(obj_type, Enum):
        return "enum"
    elif issubclass(obj_type, (str, int, float, bool, type(None))):
        return "primitive"
    elif issubclass(obj_type, (list, tuple)):
        return "sequence"
    elif issubclass(obj_type, dict):
        return "mapping"
    elif hasattr(obj_type, "__dict__"):
        return "object"
    elif hasattr(obj_type, "isoformat"):
        return "datetime"
    else:
        return "fallback"


def safe_serialize_for_json(obj, _seen=None):
    """Fonction de sérialisation sécurisée pour JSON avec cache de performance"""
    if _seen is None:
        _seen = set()

    obj_id = id(obj)
    if obj_id in _seen:
        return "<circular_reference>"

    try:
        obj_type = type(obj)
        strategy = _get_serialization_strategy(obj_type)

        # 1. Gestion des enums Python
        if strategy == "enum" or isinstance(obj, Enum):
            return obj.value

        # 2. Types primitifs JSON-safe
        if (
            strategy == "primitive"
            or obj is None
            or isinstance(obj, (str, int, float, bool))
        ):
            return obj

        # 3. Gestion des defaultdict
        if isinstance(obj, defaultdict):
            _seen.add(obj_id)
            try:
                result = {
                    str(k): safe_serialize_for_json(v, _seen) for k, v in obj.items()
                }
            finally:
                _seen.remove(obj_id)
            return result

        # 4. Listes et tuples
        if strategy == "sequence" or isinstance(obj, (list, tuple)):
            _seen.add(obj_id)
            try:
                result = [safe_serialize_for_json(item, _seen) for item in obj]
            finally:
                _seen.remove(obj_id)
            return result

        # 5. Dictionnaires
        if strategy == "mapping" or isinstance(obj, dict):
            _seen.add(obj_id)
            try:
                result = {}
                for k, v in obj.items():
                    if isinstance(k, Enum):
                        safe_key = k.value
                    elif isinstance(k, (str, int, float)):
                        safe_key = k
                    else:
                        safe_key = str(k)
                    result[safe_key] = safe_serialize_for_json(v, _seen)
            finally:
                _seen.remove(obj_id)
            return result

        # 6. Gestion des datetime et types temporels
        if strategy == "datetime" or hasattr(obj, "isoformat"):
            return obj.isoformat()

        # 7. Gestion des Decimal
        if isinstance(obj, Decimal):
            return float(obj)

        # 8. Gestion des sets
        if isinstance(obj, set):
            return list(obj)

        # 9. Gestion spéciale pour LanguageDetectionResult
        if (
            hasattr(obj, "language")
            and hasattr(obj, "confidence")
            and hasattr(obj, "source")
        ):
            _seen.add(obj_id)
            try:
                result = {
                    "language": obj.language,
                    "confidence": float(obj.confidence),
                    "source": obj.source,
                    "processing_time_ms": getattr(obj, "processing_time_ms", 0),
                }
            finally:
                _seen.remove(obj_id)
            return result

        # 10. Objets avec attributs
        if strategy == "object" or hasattr(obj, "__dict__"):
            _seen.add(obj_id)
            try:
                result = {}
                for attr_name, attr_value in obj.__dict__.items():
                    if not attr_name.startswith("_"):
                        result[attr_name] = safe_serialize_for_json(attr_value, _seen)
            finally:
                _seen.remove(obj_id)
            return result

        # 11. Gestion des bytes
        if isinstance(obj, bytes):
            try:
                return obj.decode("utf-8")
            except UnicodeDecodeError:
                return f"<bytes:{len(obj)}>"

        # 12. Fallback sécurisé
        return str(obj)

    except Exception as e:
        logger.warning(f"Erreur sérialisation objet {type(obj)}: {e}")
        return f"<serialization_error: {type(obj).__name__}>"


# ============================================================================
# GESTION MÉMOIRE TENANT OPTIMISÉE
# ============================================================================


class TenantMemory(OrderedDict):
    """Cache LRU avec TTL optimisé pour la mémoire de conversation"""

    def __init__(self):
        super().__init__()
        self.tenant_ttl = TENANT_TTL
        self.max_tenants = MAX_TENANTS
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Nettoyage toutes les 5 minutes
        self._access_count = 0

    def _cleanup_expired(self):
        """Nettoyage optimisé des entrées expirées"""
        now = time.time()

        if now - self._last_cleanup < self._cleanup_interval:
            return

        try:
            expired_keys = [
                k for k, v in self.items() if now - v.get("ts", 0) > self.tenant_ttl
            ]

            for k in expired_keys:
                del self[k]

            if expired_keys:
                logger.debug(f"Nettoyage TTL: {len(expired_keys)} tenants expirés")

            self._last_cleanup = now

        except Exception as e:
            logger.warning(f"Erreur nettoyage TTL: {e}")

    def set(self, tenant_id: str, item: list):
        """Version optimisée de set avec nettoyage intelligent"""
        if not tenant_id or not isinstance(item, list):
            logger.warning(
                f"Paramètres invalides pour TenantMemory.set: {tenant_id}, {type(item)}"
            )
            return

        now = time.time()
        self[tenant_id] = {"data": item, "ts": now, "last_query": ""}
        self.move_to_end(tenant_id)

        self._access_count += 1

        # Nettoyage TTL intelligent
        if self._access_count % 10 == 0:
            self._cleanup_expired()

        # Nettoyage LRU optimisé
        if len(self) > self.max_tenants:
            excess_count = len(self) - self.max_tenants
            for _ in range(excess_count):
                try:
                    oldest_tenant, _ = self.popitem(last=False)
                    logger.debug(f"Tenant {oldest_tenant} purgé (LRU)")
                except KeyError:
                    break

    def get(self, tenant_id: str, default=None):
        """Version optimisée de get avec validation TTL"""
        if not tenant_id or tenant_id not in self:
            return default

        try:
            now = time.time()
            tenant_data = self[tenant_id]

            # Vérification TTL
            if now - tenant_data.get("ts", 0) > self.tenant_ttl:
                del self[tenant_id]
                return default

            # Mise à jour timestamp et position LRU
            tenant_data["ts"] = now
            self.move_to_end(tenant_id)
            return tenant_data

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

    def get_stats(self) -> Dict[str, Any]:
        """Statistiques détaillées du cache"""
        now = time.time()
        active_tenants = sum(
            1 for v in self.values() if now - v.get("ts", 0) <= self.tenant_ttl
        )

        return {
            "total_tenants": len(self),
            "active_tenants": active_tenants,
            "max_tenants": self.max_tenants,
            "utilization": len(self) / self.max_tenants,
            "last_cleanup": self._last_cleanup,
            "access_count": self._access_count,
            "next_cleanup_in": max(
                0, self._cleanup_interval - (now - self._last_cleanup)
            ),
        }


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
        """Enregistre les métriques avec support LangSmith et RRF"""
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

            # Traitement des métriques temporelles
            processing_time = (
                endpoint_time
                if endpoint_time > 0
                else safe_get_attribute(result, "processing_time", 0)
            )
            if processing_time > 0:
                self.recent_processing_times.append(float(processing_time))
                if len(self.recent_processing_times) > self.max_recent_samples:
                    self.recent_processing_times.pop(0)
                if self.recent_processing_times:
                    self.endpoint_metrics["avg_processing_time"] = sum(
                        self.recent_processing_times
                    ) / len(self.recent_processing_times)

                # Calcul des percentiles
                if len(self.recent_processing_times) >= 10:
                    sorted_times = sorted(self.recent_processing_times)
                    n = len(sorted_times)
                    self.latency_percentiles["p50"] = sorted_times[int(n * 0.5)]
                    self.latency_percentiles["p95"] = sorted_times[int(n * 0.95)]
                    self.latency_percentiles["p99"] = sorted_times[int(n * 0.99)]

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
                    self.endpoint_metrics["rag_enhanced_queries"]
                    + self.endpoint_metrics["verified_responses"]
                    + self.endpoint_metrics["agent_queries"]
                )
                / total_queries,
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
                "throughput_qps": self._calculate_throughput(),
                "memory_usage": self._get_memory_stats(),
            }
        except Exception as e:
            logger.error(f"Erreur calcul métriques: {e}")
            return self.endpoint_metrics

    def _calculate_throughput(self) -> float:
        """Calcule le throughput approximatif"""
        if len(self.recent_processing_times) < 2:
            return 0.0
        avg_time = sum(self.recent_processing_times) / len(self.recent_processing_times)
        return 1.0 / max(avg_time, 0.001)

    def _get_memory_stats(self) -> Dict[str, Any]:
        """Statistiques d'utilisation mémoire"""
        return {
            "conversation_memory": conversation_memory.get_stats(),
            "metrics_samples": {
                "processing_times": len(self.recent_processing_times),
                "confidences": len(self.recent_confidences),
            },
        }


# Instance globale
metrics_collector = EndpointMetricsCollector()

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "safe_serialize_for_json",
    "TenantMemory",
    "conversation_memory",
    "add_to_conversation_memory",
    "EndpointMetricsCollector",
    "metrics_collector",
    "_get_serialization_strategy",
]

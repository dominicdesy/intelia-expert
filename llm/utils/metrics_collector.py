# -*- coding: utf-8 -*-
"""
utils/metrics_collector.py - Module de collecte de métriques
Extrait de utilities.py pour modularisation
"""

import statistics
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# ============================================================================
# COLLECTEUR DE MÉTRIQUES
# ============================================================================


class MetricsCollector:
    """Collecteur de métriques enrichi avec statistiques intent et cache sémantique"""

    def __init__(self):
        self.counters = defaultdict(int)
        self.last_100_lat = []
        self.cache_stats = defaultdict(int)
        self.search_stats = defaultdict(int)
        self.intent_stats = defaultdict(int)
        self.semantic_cache_stats = defaultdict(int)
        self.ood_stats = defaultdict(int)
        self.api_corrections = defaultdict(int)

    def inc(self, key: str, n: int = 1):
        self.counters[key] += n

    def observe_latency(self, sec: float):
        self.last_100_lat.append(sec)
        if len(self.last_100_lat) > 100:
            self.last_100_lat = self.last_100_lat[-100:]

    def cache_hit(self, cache_type: str):
        self.cache_stats[f"{cache_type}_hits"] += 1

    def cache_miss(self, cache_type: str):
        self.cache_stats[f"{cache_type}_misses"] += 1

    def intent_detected(self, intent_type: str, confidence: float):
        self.intent_stats[f"intent_{intent_type}"] += 1
        self.intent_stats["total_intents"] += 1
        self.intent_stats["avg_confidence"] = (
            self.intent_stats.get("avg_confidence", 0.0)
            * (self.intent_stats["total_intents"] - 1)
            + confidence
        ) / self.intent_stats["total_intents"]

    def semantic_cache_hit(self, cache_type: str):
        self.semantic_cache_stats[f"semantic_{cache_type}_hits"] += 1

    def semantic_fallback_used(self):
        self.semantic_cache_stats["fallback_hits"] += 1

    def ood_filtered(self, score: float, reason: str):
        """Enregistre un filtrage OOD avec détails"""
        self.ood_stats[f"ood_{reason}"] += 1
        self.ood_stats["ood_total"] += 1

        if isinstance(score, (int, float)):
            score_value = float(score)
        else:
            score_value = 0.5

        current_avg = self.ood_stats.get("avg_ood_score", 0.0)
        total_filtered = self.ood_stats["ood_total"]

        if total_filtered > 0:
            self.ood_stats["avg_ood_score"] = (
                current_avg * (total_filtered - 1) + score_value
            ) / total_filtered
        else:
            self.ood_stats["avg_ood_score"] = score_value

    def ood_accepted(self, score: float, reason: str = "accepted"):
        """Trace les requêtes acceptées après validation OOD"""
        self.ood_stats[f"ood_{reason}"] += 1
        self.ood_stats["ood_accepted_total"] += 1

        current_avg = self.ood_stats.get("avg_accepted_score", 0.0)
        total_accepted = self.ood_stats["ood_accepted_total"]
        if total_accepted > 0:
            self.ood_stats["avg_accepted_score"] = (
                current_avg * (total_accepted - 1) + score
            ) / total_accepted

    def hybrid_search_completed(
        self, results_count: int, alpha: float, duration: float, intent_type: str = None
    ):
        """Trace les recherches hybrides complétées"""
        self.search_stats["hybrid_searches"] += 1
        self.search_stats["total_results"] += results_count
        self.search_stats["total_duration"] += duration

        if intent_type:
            self.search_stats[f"intent_{intent_type}_searches"] += 1

        searches = self.search_stats["hybrid_searches"]
        if searches > 0:
            self.search_stats["avg_results_per_search"] = (
                self.search_stats["total_results"] / searches
            )
            self.search_stats["avg_duration_per_search"] = (
                self.search_stats["total_duration"] / searches
            )

    def retrieval_error(self, error_type: str, error_msg: str):
        """Trace les erreurs de récupération"""
        self.search_stats[f"error_{error_type}"] += 1
        self.search_stats["total_errors"] += 1

    def api_correction_applied(self, correction_type: str):
        self.api_corrections[correction_type] += 1

    def record_query(
        self, tenant_id: str, query: str, response_time: float, status: str, **kwargs
    ):
        """
        Enregistre les métriques complètes d'une requête

        Args:
            tenant_id: Identifiant du tenant
            query: Texte de la requête
            response_time: Temps de réponse en secondes
            status: Statut de la requête (success, error, etc.)
            **kwargs: Métriques additionnelles (source, tokens, intent, etc.)
        """
        # Incrémenter les compteurs appropriés
        self.inc(f"query_{status}")
        self.inc("total_queries")

        # Enregistrer la latence
        self.observe_latency(response_time)

        # Métriques additionnelles optionnelles
        if "source" in kwargs:
            self.search_stats[f"source_{kwargs['source']}"] += 1

        if "tokens" in kwargs:
            self.counters["total_tokens"] += kwargs["tokens"]

        if "intent" in kwargs:
            intent_type = kwargs["intent"]
            confidence = kwargs.get("confidence", 0.0)
            self.intent_detected(intent_type, confidence)

        if "cache_hit" in kwargs and kwargs["cache_hit"]:
            cache_type = kwargs.get("cache_type", "general")
            self.cache_hit(cache_type)

        # Log pour debugging
        logger.debug(
            f"Query recorded - tenant: {tenant_id}, "
            f"status: {status}, time: {response_time:.3f}s, "
            f"extras: {list(kwargs.keys())}"
        )

    def snapshot(self):
        p50 = statistics.median(self.last_100_lat) if self.last_100_lat else 0.0
        p95 = (
            sorted(self.last_100_lat)[int(0.95 * len(self.last_100_lat)) - 1]
            if len(self.last_100_lat) >= 20
            else p50
        )
        return {
            "counters": dict(self.counters),
            "cache_stats": dict(self.cache_stats),
            "search_stats": dict(self.search_stats),
            "intent_stats": dict(self.intent_stats),
            "semantic_cache_stats": dict(self.semantic_cache_stats),
            "ood_stats": dict(self.ood_stats),
            "api_corrections": dict(self.api_corrections),
            "p50_latency_sec": round(p50, 3),
            "p95_latency_sec": round(p95, 3),
            "samples": len(self.last_100_lat),
        }

    def as_json(self) -> dict:
        """Export JSON des métriques pour l'app"""
        return {
            "cache": self.cache_stats,
            "ood": self.ood_stats,
            "guardrails": self.api_corrections,
        }


# Instance globale
METRICS = MetricsCollector()


def get_all_metrics_json(
    metrics_instance: MetricsCollector, extra: dict = None
) -> dict:
    """Fonction d'export JSON consolidée des métriques avec données supplémentaires"""
    data = metrics_instance.as_json()
    if extra:
        data.update(extra)
    return data

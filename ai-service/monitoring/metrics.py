# -*- coding: utf-8 -*-
"""
Monitoring basique avec OpenTelemetry et Prometheus
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Monitoring basique avec OpenTelemetry et Prometheus
"""

import time
import logging
from typing import Dict, Any
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collecteur de métriques simple
    Compatible OpenTelemetry et Prometheus
    """

    def __init__(self):
        self.metrics: Dict[str, Any] = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0.0,
                "errors": 0,
                "last_reset": datetime.now(),
            }
        )

        self.start_time = time.time()

    def record_request(self, endpoint: str, duration: float, error: bool = False):
        """
        Enregistre une requête

        Args:
            endpoint: Nom de l'endpoint (/chat, /question, etc.)
            duration: Durée en secondes
            error: True si erreur
        """
        metric = self.metrics[endpoint]
        metric["count"] += 1
        metric["total_time"] += duration
        if error:
            metric["errors"] += 1

    def record_cache_hit(self, cache_type: str):
        """Enregistre un cache hit"""
        self.metrics[f"cache_{cache_type}_hits"]["count"] += 1

    def record_cache_miss(self, cache_type: str):
        """Enregistre un cache miss"""
        self.metrics[f"cache_{cache_type}_misses"]["count"] += 1

    def record_openai_call(self, model: str, tokens: int, duration: float):
        """Enregistre un appel OpenAI"""
        key = f"openai_{model}"
        self.metrics[key]["count"] += 1
        self.metrics[key]["total_tokens"] = (
            self.metrics[key].get("total_tokens", 0) + tokens
        )
        self.metrics[key]["total_time"] += duration

    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques actuelles
        """
        uptime = time.time() - self.start_time

        stats = {"uptime_seconds": uptime, "endpoints": {}, "cache": {}, "openai": {}}

        for key, metric in self.metrics.items():
            if key.startswith("cache_"):
                stats["cache"][key] = metric
            elif key.startswith("openai_"):
                stats["openai"][key] = metric
            else:
                # Calculer moyenne
                avg_time = (
                    metric["total_time"] / metric["count"] if metric["count"] > 0 else 0
                )
                stats["endpoints"][key] = {
                    **metric,
                    "avg_time": avg_time,
                    "error_rate": (
                        metric["errors"] / metric["count"] if metric["count"] > 0 else 0
                    ),
                }

        return stats

    def reset(self):
        """Reset toutes les métriques"""
        self.metrics.clear()
        self.start_time = time.time()


# Instance globale
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Retourne l'instance globale du collecteur"""
    return _metrics_collector

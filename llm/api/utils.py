"""
Utilitaires communs pour l'API
Ce module contient des fonctions et objets partagés pour éviter les importations circulaires
"""

import logging
from typing import Any, Dict
from datetime import datetime
from collections import deque
from decimal import Decimal

logger = logging.getLogger(__name__)


# ============================================================================
# SÉRIALISATION JSON
# ============================================================================


def safe_serialize_for_json(obj: Any) -> Any:
    """
    Sérialise un objet pour le rendre compatible JSON.
    Gère les types datetime, Decimal, bytes, etc.

    Args:
        obj: L'objet à sérialiser

    Returns:
        L'objet sérialisé ou l'objet original si déjà compatible JSON
    """
    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, Decimal):
        return float(obj)

    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except Exception:
            return str(obj)

    if isinstance(obj, dict):
        return {k: safe_serialize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set, deque)):
        return [safe_serialize_for_json(item) for item in obj]

    # Pour les autres types, convertir en string
    try:
        return str(obj)
    except Exception:
        return repr(obj)


# ============================================================================
# MÉMOIRE DE CONVERSATION
# ============================================================================

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


# ============================================================================
# COLLECTEUR DE MÉTRIQUES
# ============================================================================


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

    def get_stats(self) -> Dict[str, Any]:
        """Alias pour get_metrics pour compatibilité"""
        return self.get_metrics()


# Instance globale du collecteur de métriques
metrics_collector = MetricsCollector()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "safe_serialize_for_json",
    "conversation_memory",
    "add_to_conversation_memory",
    "metrics_collector",
    "MetricsCollector",
]

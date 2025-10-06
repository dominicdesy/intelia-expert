# -*- coding: utf-8 -*-
"""
rag_postgresql_router.py - Routeur intelligent pour types de requêtes
"""

import logging
from .rag_postgresql_models import QueryType

logger = logging.getLogger(__name__)


class QueryRouter:
    """Routeur intelligent pour déterminer le type de requête"""

    def __init__(self):
        self.metric_keywords = {
            "performance",
            "metrics",
            "donnees",
            "chiffres",
            "resultats",
            "weight",
            "poids",
            "egg",
            "oeuf",
            "production",
            "feed",
            "alimentation",
            "mortality",
            "mortalite",
            "growth",
            "croissance",
            "fcr",
            "icg",
            "conversion",
            "ross",
            "cobb",
            "hubbard",
        }

        self.knowledge_keywords = {
            "comment",
            "pourquoi",
            "qu'est-ce",
            "expliquer",
            "definir",
            "maladie",
            "disease",
            "traitement",
            "prevention",
            "biosecurite",
        }

    def route_query(self, query: str, intent_result=None) -> QueryType:
        """Détermine le type de requête basé sur les mots-clés"""
        query_lower = query.lower()

        metric_score = sum(
            1 for keyword in self.metric_keywords if keyword in query_lower
        )
        knowledge_score = sum(
            1 for keyword in self.knowledge_keywords if keyword in query_lower
        )

        if metric_score > knowledge_score + 1:
            return QueryType.METRICS
        elif knowledge_score > metric_score + 1:
            return QueryType.KNOWLEDGE
        else:
            return QueryType.HYBRID

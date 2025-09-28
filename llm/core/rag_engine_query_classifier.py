# -*- coding: utf-8 -*-
"""
rag_engine_query_classifier.py - Classification intelligente des requêtes
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class QueryClassifier:
    """Classificateur intelligent pour le routage des requêtes"""

    def classify_query(self, query: str, entities: Dict, is_comparative: bool) -> str:
        """
        Classification précise du type de requête pour un routage optimal

        Returns:
            "temporal_range" | "comparative" | "standard"
        """

        # 1. Détection prioritaire des plages temporelles (entre X et Y jours)
        if self._is_temporal_range_query(query):
            logger.debug("Plage temporelle détectée")
            return "temporal_range"

        # 2. Détection des vraies comparaisons (X vs Y, différence entre X et Y)
        if self._is_comparative_query(query, entities, is_comparative):
            logger.debug("Requête comparative confirmée")
            return "comparative"

        # 3. Par défaut : requête standard
        return "standard"

    def _is_temporal_range_query(self, query: str) -> bool:
        """Détecte les plages temporelles"""
        temporal_patterns = [
            r"entre\s+\d+\s+et\s+\d+\s+jours?",
            r"de\s+\d+\s+à\s+\d+\s+jours?",
            r"\d+\s*-\s*\d+\s+jours?",
            r"from\s+\d+\s+to\s+\d+\s+days?",
        ]

        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in temporal_patterns)

    def _is_comparative_query(
        self, query: str, entities: Dict, is_comparative: bool
    ) -> bool:
        """Détecte les vraies comparaisons"""
        # Patterns comparatifs
        comparative_patterns = [
            r"(différence|compare|vs|versus|contre)",
            r"(entre\s+\w+\s+et\s+\w+)",
            r"(quel\s+est\s+le\s+meilleur)",
        ]

        query_lower = query.lower()
        has_comparative_pattern = any(
            re.search(pattern, query_lower) for pattern in comparative_patterns
        )

        if has_comparative_pattern:
            # Vérifier qu'il y a vraiment plusieurs entités à comparer
            comparison_entities = entities.get("comparison_entities", [])
            if len(comparison_entities) >= 2 or is_comparative:
                return True
            else:
                logger.debug("Pattern comparatif mais entités insuffisantes")
                return False

        # Vérification comparative basée sur preprocessing
        if is_comparative:
            comparison_entities = entities.get("comparison_entities", [])
            if len(comparison_entities) >= 2:
                return True
            else:
                logger.debug("Marquée comparative mais entités insuffisantes")
                return False

        return False

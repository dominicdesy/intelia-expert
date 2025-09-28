# -*- coding: utf-8 -*-
"""
rag_postgresql_normalizer.py - Normaliseur de requêtes SQL multilingue
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


class SQLQueryNormalizer:
    """Normaliseur multilingue pour requêtes SQL"""

    def __init__(self):
        self.terminology = self._load_terminology()
        self.CONCEPT_MAPPINGS = self._build_concept_mappings()
        logger.info(
            f"SQLQueryNormalizer initialized with {len(self.CONCEPT_MAPPINGS)} concept mappings"
        )

    def _load_terminology(self) -> Dict[str, Any]:
        """Charge la terminologie depuis les fichiers JSON de configuration"""
        config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
        terms = {}
        supported_languages = ["en", "fr", "es"]

        for lang in supported_languages:
            file_path = os.path.join(config_dir, f"universal_terms_{lang}.json")
            try:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        terms[lang] = json.load(f)
                        logger.info(
                            f"Terminology loaded successfully for language: {lang}"
                        )
                else:
                    logger.warning(f"Terminology file not found: {file_path}")
                    terms[lang] = {}
            except Exception as e:
                logger.error(f"Error loading terminology for {lang}: {e}")
                terms[lang] = {}

        return terms

    def _build_concept_mappings(self) -> Dict[str, List[str]]:
        """Construit les mappings de concepts depuis la terminologie chargée"""
        mappings = {}

        for lang, lang_terms in self.terminology.items():
            if "performance_metrics" not in lang_terms:
                continue

            perf_metrics = lang_terms["performance_metrics"]

            for metric_key, metric_terms in perf_metrics.items():
                base_key = metric_key.split("_")[0] if "_" in metric_key else metric_key

                if base_key not in mappings:
                    mappings[base_key] = []

                if isinstance(metric_terms, list):
                    mappings[base_key].extend(metric_terms)

                if metric_key not in mappings:
                    mappings[metric_key] = []
                if isinstance(metric_terms, list):
                    mappings[metric_key].extend(metric_terms)

        # Supprimer les doublons
        for key in mappings:
            mappings[key] = list(set(mappings[key]))

        logger.info(f"Built concept mappings for {len(mappings)} concepts")
        return mappings

    def get_search_terms(self, query: str) -> Tuple[List[str], List[str]]:
        """Retourne (normalized_concepts, raw_words) pour recherche SQL"""
        normalized = self.normalize_query_concepts(query)
        raw_words = [word for word in query.lower().split() if len(word) > 3]
        return normalized, raw_words

    def normalize_query_concepts(self, query: str) -> List[str]:
        """Convertit une requête utilisateur en termes de concept normalisés"""
        query_lower = query.lower()
        normalized_concepts = []

        for concept, terms in self.CONCEPT_MAPPINGS.items():
            if any(term.lower() in query_lower for term in terms):
                normalized_concepts.extend(terms)

        # Supprimer les doublons en conservant l'ordre
        seen = set()
        unique_concepts = []
        for concept in normalized_concepts:
            if concept not in seen:
                seen.add(concept)
                unique_concepts.append(concept)

        return unique_concepts

    def extract_sex_from_query(self, query: str) -> Optional[str]:
        """Extrait le sexe de la requête"""
        query_lower = query.lower()

        male_patterns = ["male", "mâle", "mâles", "masculin", "coq", "coqs", "rooster"]
        if any(pattern in query_lower for pattern in male_patterns):
            return "male"

        female_patterns = [
            "female",
            "femelle",
            "femelles",
            "féminin",
            "poule",
            "poules",
            "hen",
        ]
        if any(pattern in query_lower for pattern in female_patterns):
            return "female"

        mixed_patterns = [
            "as-hatched",
            "ashatched",
            "mixed",
            "mixte",
            "mélangé",
            "non sexé",
            "straight run",
        ]
        if any(pattern in query_lower for pattern in mixed_patterns):
            return "as_hatched"

        return None

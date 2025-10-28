# -*- coding: utf-8 -*-
"""
rag_postgresql_normalizer.py - Normaliseur de requêtes SQL multilingue
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
rag_postgresql_normalizer.py - Normaliseur de requêtes SQL multilingue
Version corrigée: Gestion correcte de la structure JSON avec domains
"""

import os
import json
import logging
from utils.types import Dict, List, Optional, Any, Tuple

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
        # Fix: Use absolute path to /app/config instead of relative path
        config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config")
        terms = {}
        supported_languages = [
            "en",
            "fr",
            "es",
            "de",
            "it",
            "pt",
            "pl",
            "nl",
            "id",
            "hi",
            "zh",
            "th",
        ]

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
        """
        Construit les mappings de concepts depuis la terminologie chargée

        CORRECTION: Gère correctement la structure JSON avec:
        - Accès via lang_terms["domains"]["performance_metrics"]
        - Structure {canonical, confidence, variants} au lieu de listes simples
        """
        mappings = {}
        total_concepts_found = 0

        for lang, lang_terms in self.terminology.items():
            # CORRECTION 1: Vérifier l'existence de "domains"
            if "domains" not in lang_terms:
                logger.warning(f"No 'domains' key found in terminology for {lang}")
                continue

            domains = lang_terms["domains"]

            # CORRECTION 2: Accéder à performance_metrics via domains
            if "performance_metrics" not in domains:
                logger.warning(f"No 'performance_metrics' in domains for {lang}")
                continue

            perf_metrics = domains["performance_metrics"]
            lang_concepts_count = 0

            for metric_key, metric_data in perf_metrics.items():
                # CORRECTION 3: Gérer la structure dict avec variants
                if not isinstance(metric_data, dict):
                    logger.debug(f"Skipping {metric_key} - not a dict structure")
                    continue

                # Extraire les variants de la structure
                variants = metric_data.get("variants", [])
                canonical = metric_data.get("canonical", "")

                if not variants:
                    logger.debug(f"No variants found for {metric_key} in {lang}")
                    continue

                # Créer mapping pour la clé de base (premier mot)
                base_key = metric_key.split("_")[0] if "_" in metric_key else metric_key

                if base_key not in mappings:
                    mappings[base_key] = []
                mappings[base_key].extend(variants)

                # Ajouter aussi le canonical si présent
                if canonical and canonical not in mappings[base_key]:
                    mappings[base_key].append(canonical)

                # Créer mapping pour la clé complète
                if metric_key not in mappings:
                    mappings[metric_key] = []
                mappings[metric_key].extend(variants)

                if canonical and canonical not in mappings[metric_key]:
                    mappings[metric_key].append(canonical)

                lang_concepts_count += 1

            logger.debug(f"Loaded {lang_concepts_count} concepts from {lang}")
            total_concepts_found += lang_concepts_count

        # Supprimer les doublons et nettoyer
        for key in mappings:
            mappings[key] = list(set(mappings[key]))
            # Trier pour cohérence
            mappings[key].sort()

        logger.info(
            f"Built concept mappings for {len(mappings)} concepts "
            f"({total_concepts_found} total entries from all languages)"
        )

        # Log détaillé si aucun concept trouvé (debugging)
        if len(mappings) == 0:
            logger.error(
                "No concept mappings built! Check JSON structure. "
                "Expected: {domains: {performance_metrics: {metric_key: {variants: [...]}}}}"
            )

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

    def get_concept_info(self, concept_key: str) -> Dict[str, Any]:
        """
        Retourne les informations détaillées sur un concept

        Args:
            concept_key: Clé du concept (ex: "feed_conversion_ratio")

        Returns:
            Dict avec variants et statistiques
        """
        if concept_key not in self.CONCEPT_MAPPINGS:
            return {"exists": False, "variants": [], "count": 0}

        variants = self.CONCEPT_MAPPINGS[concept_key]
        return {
            "exists": True,
            "variants": variants,
            "count": len(variants),
            "sample": variants[:5] if len(variants) > 5 else variants,
        }

    def debug_mappings(self) -> str:
        """Retourne un résumé détaillé des mappings pour debugging"""
        lines = [
            "=== CONCEPT MAPPINGS DEBUG ===",
            f"Total concepts: {len(self.CONCEPT_MAPPINGS)}",
            "",
        ]

        for concept, variants in sorted(self.CONCEPT_MAPPINGS.items()):
            lines.append(f"{concept}:")
            lines.append(f"  - {len(variants)} variants")
            lines.append(f"  - Sample: {', '.join(variants[:3])}...")
            lines.append("")

        return "\n".join(lines)


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("=" * 70)
    print("TESTS SQL QUERY NORMALIZER - VERSION CORRIGÉE")
    print("=" * 70)

    # Test 1: Initialisation
    print("\nTest 1: Initialisation")
    try:
        normalizer = SQLQueryNormalizer()
        print(f"✅ Normalizer initialisé: {len(normalizer.CONCEPT_MAPPINGS)} concepts")

        if len(normalizer.CONCEPT_MAPPINGS) == 0:
            print("⚠️  ATTENTION: Aucun concept chargé!")
            print("    Vérifiez la structure des fichiers JSON")
        else:
            print(
                f"✅ Concepts disponibles: {list(normalizer.CONCEPT_MAPPINGS.keys())[:5]}..."
            )
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Normalisation de requêtes
    print("\nTest 2: Normalisation de requêtes")
    test_queries = [
        "What is the optimal FCR for Ross 308?",
        "Quelle est la consommation d'eau moyenne?",
        "Average daily gain for broilers",
    ]

    for query in test_queries:
        concepts = normalizer.normalize_query_concepts(query)
        print(f"Query: {query}")
        print(f"  Concepts: {concepts[:5] if len(concepts) > 5 else concepts}")

    # Test 3: Extraction du sexe
    print("\nTest 3: Extraction du sexe")
    sex_queries = [
        ("Ross 308 male performance", "male"),
        ("Poules pondeuses femelles", "female"),
        ("As-hatched broilers", "as_hatched"),
    ]

    for query, expected in sex_queries:
        result = normalizer.extract_sex_from_query(query)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{query}' → {result} (expected: {expected})")

    # Test 4: Info sur un concept
    print("\nTest 4: Info détaillée sur les concepts")
    test_concepts = ["feed_conversion_ratio", "body_weight", "mortality"]

    for concept in test_concepts:
        info = normalizer.get_concept_info(concept)
        if info["exists"]:
            print(f"✅ {concept}: {info['count']} variants")
            print(f"   Sample: {', '.join(info['sample'])}")
        else:
            print(f"❌ {concept}: Non trouvé")

    # Test 5: Debug complet
    print("\nTest 5: Résumé complet des mappings")
    print(normalizer.debug_mappings())

    print("\n" + "=" * 70)
    print("TESTS TERMINÉS")
    print("=" * 70)

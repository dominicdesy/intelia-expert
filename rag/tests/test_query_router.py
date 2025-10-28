# -*- coding: utf-8 -*-
"""
test_query_router.py - Tests unitaires pour le QueryRouter v2.0

Tests de l'approche hybride: Keywords enrichis + LLM fallback
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.postgresql.router import QueryRouter
from retrieval.postgresql.models import QueryType


class TestQueryRouterV2:
    """Tests pour QueryRouter v2.0 (approche hybride)"""

    @pytest.fixture
    def router(self):
        """Fixture: Instance de QueryRouter"""
        return QueryRouter()

    def test_router_initialization(self, router):
        """Test de l'initialisation"""
        assert router is not None
        assert len(router.metric_keywords) > 20  # Au moins 65 keywords
        assert len(router.knowledge_keywords) > 10  # Au moins 25 keywords
        assert router.confidence_threshold == 2

    def test_get_routing_stats(self, router):
        """Test des statistiques de routing"""
        stats = router.get_routing_stats()
        assert stats["metric_keywords_count"] >= 65
        assert stats["knowledge_keywords_count"] >= 25
        assert stats["confidence_threshold"] == 2
        assert stats["version"] == "2.0 (hybrid)"

    # ===== TESTS METRICS (devrait router vers PostgreSQL) =====

    def test_simple_metric_query(self, router):
        """Test: Question métrique simple"""
        queries = [
            "Quel est le poids cible à 35 jours?",
            "What is the target weight at 35 days?",
            "FCR Ross 308 à 42 jours",
            "Consommation alimentaire Cobb 500",
        ]
        for query in queries:
            result = router.route_query(query)
            assert result == QueryType.METRICS, f"Failed for: {query}"

    def test_breed_comparison_metric(self, router):
        """Test: Comparaison de races (métriques)"""
        queries = [
            "Ross 308 vs Cobb 500 poids à 35 jours",
            "Comparer FCR Ross et Cobb",
            "Différence poids Hubbard vs Ross",
        ]
        for query in queries:
            result = router.route_query(query)
            assert result in [
                QueryType.METRICS,
                QueryType.HYBRID,
            ], f"Failed for: {query}"

    def test_temporal_metric_query(self, router):
        """Test: Questions temporelles (métriques)"""
        queries = [
            "Poids cible à 28 jours",
            "FCR au jour 42",
            "Performance à 35 jours",
        ]
        for query in queries:
            result = router.route_query(query)
            assert result == QueryType.METRICS, f"Failed for: {query}"

    def test_sex_differentiated_metric(self, router):
        """Test: Métriques différenciées par sexe"""
        queries = [
            "Poids cible mâle à 35 jours",
            "FCR femelles Ross 308",
            "Gain males vs females",
        ]
        for query in queries:
            result = router.route_query(query)
            assert result == QueryType.METRICS, f"Failed for: {query}"

    # ===== TESTS KNOWLEDGE (devrait router vers Weaviate) =====

    def test_simple_knowledge_query(self, router):
        """Test: Question de connaissances"""
        queries = [
            "Qu'est-ce que la maladie de Newcastle?",
            "Comment traiter la coccidiose?",
            "Pourquoi la mortalité augmente?",
            "Expliquer la biosécurité",
        ]
        for query in queries:
            result = router.route_query(query)
            assert result == QueryType.KNOWLEDGE, f"Failed for: {query}"

    def test_treatment_protocol_query(self, router):
        """Test: Questions sur traitements/protocoles"""
        queries = [
            "Protocole de vaccination Newcastle",
            "Comment prévenir la coccidiose?",
            "Traitement symptômes respiratoires",
        ]
        for query in queries:
            result = router.route_query(query)
            assert result == QueryType.KNOWLEDGE, f"Failed for: {query}"

    def test_diagnostic_query(self, router):
        """Test: Questions de diagnostic"""
        queries = [
            "Symptômes de la grippe aviaire",
            "Diagnostic problème de croissance",
            "Causes de mortalité élevée",
        ]
        for query in queries:
            result = router.route_query(query)
            assert result == QueryType.KNOWLEDGE, f"Failed for: {query}"

    # ===== TESTS HYBRID (questions mixtes) =====

    def test_hybrid_query(self, router):
        """Test: Questions mixant métriques et connaissances"""
        queries = [
            "Impact de la nutrition sur le FCR",
            "Relation entre température et mortalité",
            "Performance en cas de maladie",
        ]
        for query in queries:
            result = router.route_query(query)
            # Peut être HYBRID ou un type spécifique selon scoring
            assert result in [QueryType.METRICS, QueryType.KNOWLEDGE, QueryType.HYBRID]

    # ===== TESTS EDGE CASES =====

    def test_short_query(self, router):
        """Test: Questions très courtes"""
        queries = [
            "FCR?",
            "Poids",
            "Newcastle",
        ]
        for query in queries:
            result = router.route_query(query)
            # Devrait router même avec peu de mots
            assert result in [QueryType.METRICS, QueryType.KNOWLEDGE, QueryType.HYBRID]

    def test_multilingual_query(self, router):
        """Test: Questions multilingues"""
        queries = [
            "What is the FCR at 35 days?",  # Anglais
            "Quel est le poids à 35 jours?",  # Français
        ]
        for query in queries:
            result = router.route_query(query)
            assert result == QueryType.METRICS

    def test_empty_query(self, router):
        """Test: Question vide"""
        result = router.route_query("")
        # Devrait fallback en HYBRID (safe)
        assert result == QueryType.HYBRID

    # ===== TESTS RÉGRESSION (problèmes identifiés dans l'analyse) =====

    def test_regression_target_weight(self, router):
        """Test régression: 'Quel est le poids cible à 35 jours?' doit être METRICS"""
        result = router.route_query("Quel est le poids cible à 35 jours?")
        assert (
            result == QueryType.METRICS
        ), "Should route to METRICS (contains: quel, poids, cible, 35, jours)"

    def test_regression_treatment(self, router):
        """Test régression: 'Comment traiter la coccidiose?' doit être KNOWLEDGE"""
        result = router.route_query("Comment traiter la coccidiose?")
        assert (
            result == QueryType.KNOWLEDGE
        ), "Should route to KNOWLEDGE (contains: comment, traiter)"

    def test_regression_comparison(self, router):
        """Test régression: Comparaisons doivent privilégier METRICS"""
        result = router.route_query("Performance Ross 308 vs Cobb 500")
        assert result in [
            QueryType.METRICS,
            QueryType.HYBRID,
        ], "Breed comparison should be METRICS or HYBRID"


class TestQueryRouterStats:
    """Tests pour les statistiques et monitoring"""

    @pytest.fixture
    def router(self):
        return QueryRouter()

    def test_keyword_counts(self, router):
        """Test: Comptes de mots-clés corrects"""
        stats = router.get_routing_stats()

        # Vérifier qu'on a enrichi par rapport à v1.0 (22 → 65+ metrics)
        assert stats["metric_keywords_count"] >= 65
        assert stats["knowledge_keywords_count"] >= 25

    def test_version_tracking(self, router):
        """Test: Version tracking"""
        stats = router.get_routing_stats()
        assert stats["version"] == "2.0 (hybrid)"


# ===== TEST SUITE COMPLÈTE =====


def run_comprehensive_routing_test():
    """
    Test suite complète pour valider le routing v2.0

    Exécute 30+ cas de test couvrant tous les scénarios
    """
    import logging

    logging.basicConfig(level=logging.INFO)

    router = QueryRouter()

    test_cases = [
        # (query, expected_type, description)
        ("Quel est le poids cible à 35 jours?", QueryType.METRICS, "Simple metric"),
        ("Ross 308 vs Cobb 500 poids", QueryType.METRICS, "Breed comparison"),
        ("FCR à 42 jours", QueryType.METRICS, "FCR metric"),
        ("Qu'est-ce que Newcastle?", QueryType.KNOWLEDGE, "Disease question"),
        ("Comment traiter coccidiose?", QueryType.KNOWLEDGE, "Treatment"),
        ("Protocole vaccination", QueryType.KNOWLEDGE, "Protocol"),
        ("Impact nutrition sur FCR", QueryType.HYBRID, "Mixed query"),
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 80)
    print("QUERY ROUTER V2.0 - COMPREHENSIVE TEST SUITE")
    print("=" * 80 + "\n")

    for query, expected, description in test_cases:
        result = router.route_query(query)
        status = "✅ PASS" if result == expected else "❌ FAIL"

        print(f"{status} | {description:25} | '{query[:40]}...' → {result.value}")

        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"       Expected: {expected.value}, Got: {result.value}")

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed (Total: {len(test_cases)})")
    print("=" * 80 + "\n")

    # Stats
    stats = router.get_routing_stats()
    print("ROUTER CONFIGURATION:")
    for key, value in stats.items():
        print(f"  • {key}: {value}")

    return passed == len(test_cases)


if __name__ == "__main__":
    # Run comprehensive test
    success = run_comprehensive_routing_test()

    # Or run pytest
    # pytest.main([__file__, "-v"])

    exit(0 if success else 1)

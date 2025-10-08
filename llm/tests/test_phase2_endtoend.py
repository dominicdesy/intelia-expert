# -*- coding: utf-8 -*-
"""
test_phase2_endtoend.py - Tests End-to-End Phase 2
Valide tous les modules Phase 2 avec cas réels
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from retrieval.postgresql.router import QueryRouter
from retrieval.postgresql.models import QueryType
from processing.context_manager import get_context_manager
from processing.query_expander import get_query_expander


class TestQueryRouterPhase2:
    """Tests QueryRouter v3.0 avec tous les modules Phase 2"""

    @pytest.fixture(autouse=True)
    def reset_context(self):
        """Auto-reset ContextManager before each test"""
        from processing.context_manager import get_context_manager
        cm = get_context_manager()
        cm.reset()
        yield
        cm.reset()  # Clean up after test too

    @pytest.fixture
    def router(self):
        """Fixture: QueryRouter avec ContextManager"""
        return QueryRouter(use_context_manager=True)

    @pytest.fixture
    def context_manager(self):
        """Fixture: ContextManager singleton"""
        return get_context_manager()

    # ==================== LAYER 1: Keywords Matching ====================

    def test_metrics_simple_ross308(self, router):
        """Test: Question métrique simple Ross 308"""
        result = router.route_query("Quel est le poids Ross 308 à 35 jours?")
        assert result == QueryType.METRICS

    def test_metrics_fcr_cobb500(self, router):
        """Test: FCR Cobb 500"""
        result = router.route_query("FCR Cobb 500 à 42 jours mâles")
        assert result == QueryType.METRICS

    def test_metrics_performance(self, router):
        """Test: Performance générale"""
        result = router.route_query("Performance poulet à 28 jours")
        assert result == QueryType.METRICS

    def test_knowledge_disease(self, router):
        """Test: Question maladie"""
        result = router.route_query("Comment traiter la coccidiose?")
        assert result == QueryType.KNOWLEDGE

    def test_knowledge_newcastle(self, router):
        """Test: Maladie Newcastle"""
        result = router.route_query("Qu'est-ce que Newcastle?")
        assert result == QueryType.KNOWLEDGE

    def test_knowledge_vaccination(self, router):
        """Test: Protocole vaccination"""
        result = router.route_query("Protocole de vaccination poulet de chair")
        assert result == QueryType.KNOWLEDGE

    # ==================== LAYER 0: ContextManager ====================

    def test_context_coreference_sex(self, router, context_manager):
        """Test: Coréférence avec changement de sexe"""
        # Reset context
        context_manager.reset()

        # Première query établit le contexte
        router.route_query("Poids Ross 308 à 35 jours mâles")

        # Deuxième query avec coréférence
        result = router.route_query("Et pour les femelles?")

        # Doit être METRICS (pas HYBRID)
        assert result == QueryType.METRICS

    def test_context_coreference_breed(self, router, context_manager):
        """Test: Coréférence avec changement de breed"""
        context_manager.reset()

        router.route_query("FCR Ross 308 à 42 jours")
        result = router.route_query("Même chose pour Cobb 500")

        assert result == QueryType.METRICS

    def test_context_expansion_age(self, context_manager):
        """Test: Expansion avec contexte d'âge"""
        context_manager.reset()

        context_manager.update_context("Ross 308 à 35 jours")
        expanded = context_manager.expand_query("Et le FCR?")

        assert "ross" in expanded.lower() or "308" in expanded
        assert "35" in expanded or "jours" in expanded.lower()

    def test_context_breed_extraction(self, context_manager):
        """Test: Extraction de breed"""
        entities = context_manager.extract_entities("Performance Cobb 500")
        assert entities.get('breed', '').lower() in ['cobb 500', 'cobb', '500']

    def test_context_age_extraction(self, context_manager):
        """Test: Extraction d'âge"""
        entities = context_manager.extract_entities("Poids à 28 jours")
        assert '28' in entities.get('age', '')

    # ==================== LAYER 2: LLM Fallback ====================

    def test_ambiguous_query_hybrid(self, router):
        """Test: Question ambiguë → HYBRID"""
        result = router.route_query("Les résultats")
        # Devrait passer au LLM fallback et retourner HYBRID
        assert result in [QueryType.HYBRID, QueryType.METRICS]

    def test_short_query_fallback(self, router):
        """Test: Question très courte"""
        result = router.route_query("Poids?")
        # Low confidence → LLM fallback
        assert result in [QueryType.METRICS, QueryType.HYBRID]

    # ==================== Tests Multi-Critères ====================

    def test_multi_criteria_breed_age_sex(self, router):
        """Test: Breed + Age + Sex"""
        result = router.route_query("Poids Ross 308 mâles 35 jours")
        assert result == QueryType.METRICS

    def test_multi_criteria_fcr_breed(self, router):
        """Test: FCR + Breed"""
        result = router.route_query("Indice de conversion Hubbard")
        assert result == QueryType.METRICS

    def test_multi_criteria_knowledge_disease_prevention(self, router):
        """Test: Maladie + Prévention"""
        result = router.route_query("Prévention Gumboro poulet")
        assert result == QueryType.KNOWLEDGE

    # ==================== Tests Comparaisons ====================

    def test_comparison_breeds(self, router):
        """Test: Comparaison breeds"""
        result = router.route_query("Différence FCR entre Ross 308 et Cobb 500")
        assert result == QueryType.METRICS

    def test_comparison_vs(self, router):
        """Test: Comparaison avec 'vs'"""
        result = router.route_query("Ross 308 vs Cobb 500 performance")
        assert result == QueryType.METRICS

    # ==================== Tests Edge Cases ====================

    def test_empty_query(self, router):
        """Test: Query vide"""
        result = router.route_query("")
        assert result == QueryType.HYBRID  # Safe fallback

    def test_numbers_only(self, router):
        """Test: Seulement des chiffres"""
        result = router.route_query("308 35")
        assert result in [QueryType.METRICS, QueryType.HYBRID]

    def test_mixed_language(self, router):
        """Test: Mélange FR/EN"""
        result = router.route_query("Quel est le weight Ross 308?")
        assert result == QueryType.METRICS

    # ==================== Tests Routing Stats ====================

    def test_routing_stats(self, router):
        """Test: Statistiques routing"""
        stats = router.get_routing_stats()

        assert stats['metric_keywords_count'] == 76
        assert stats['knowledge_keywords_count'] == 50  # Updated: added disease names
        assert stats['confidence_threshold'] == 2
        assert stats['version'] == "2.0 (hybrid)"


class TestQueryExpanderPhase2:
    """Tests QueryExpander avec VocabularyExtractor"""

    @pytest.fixture
    def expander(self):
        """Fixture: QueryExpander singleton"""
        return get_query_expander()

    def test_expander_initialization(self, expander):
        """Test: Initialisation sans erreur"""
        assert expander is not None
        assert expander.alias_mappings is not None
        assert expander.metrics_vocabulary is not None

    def test_expand_query_ross308(self, expander):
        """Test: Expansion query Ross 308"""
        original = "Ross 308 poids"
        expanded = expander.expand_query(original)

        # Devrait contenir des expansions
        assert len(expanded) >= len(original)

    def test_expand_query_fcr(self, expander):
        """Test: Expansion FCR"""
        original = "FCR"
        expanded = expander.expand_query(original)

        # Devrait ajouter des termes liés
        assert "conversion" in expanded.lower() or len(expanded) > len(original)

    def test_expand_query_sex_fallback(self, expander):
        """Test: Expansion sexe/as-hatched"""
        original = "poids mâles"
        expanded = expander.expand_query(original)

        # Devrait ajouter as-hatched pour élargir
        assert "as-hatched" in expanded.lower() or "mixed" in expanded.lower()


class TestContextManagerPhase2:
    """Tests ContextManager avancés"""

    @pytest.fixture
    def manager(self):
        """Fixture: ContextManager singleton"""
        cm = get_context_manager()
        cm.reset()
        return cm

    def test_is_coreference_et_pour(self, manager):
        """Test: Détection 'Et pour...'"""
        assert manager.is_coreference("Et pour les femelles?") is True

    def test_is_coreference_meme_chose(self, manager):
        """Test: Détection 'Même chose...'"""
        assert manager.is_coreference("Même chose pour Cobb 500") is True

    def test_is_coreference_normal(self, manager):
        """Test: Non-coréférence"""
        assert manager.is_coreference("Poids Ross 308") is False

    def test_entity_extraction_complete(self, manager):
        """Test: Extraction complète"""
        entities = manager.extract_entities("Poids Ross 308 mâles 35 jours")

        assert 'ross' in entities.get('breed', '').lower()
        assert 'mâles' in entities.get('sex', '').lower() or 'male' in entities.get('sex', '').lower()
        assert '35' in entities.get('age', '')

    def test_context_summary(self, manager):
        """Test: Résumé contexte"""
        manager.update_context("Ross 308 à 35 jours mâles")
        summary = manager.get_context_summary()

        assert 'ross' in summary.lower() or '308' in summary
        assert '35' in summary


class TestIntegrationPhase2:
    """Tests d'intégration complets"""

    @pytest.fixture(autouse=True)
    def reset_context(self):
        """Auto-reset ContextManager before each test"""
        from processing.context_manager import get_context_manager
        cm = get_context_manager()
        cm.reset()
        yield
        cm.reset()  # Clean up after test too

    def test_full_flow_metrics_query(self):
        """Test: Flow complet query métrique"""
        router = QueryRouter(use_context_manager=True)

        # Query simple
        result1 = router.route_query("Poids Ross 308 à 35 jours")
        assert result1 == QueryType.METRICS

        # Query avec contexte
        result2 = router.route_query("Et pour les femelles?")
        assert result2 == QueryType.METRICS

    def test_full_flow_knowledge_query(self):
        """Test: Flow complet query knowledge"""
        router = QueryRouter(use_context_manager=True)

        result = router.route_query("Comment prévenir la coccidiose?")
        assert result == QueryType.KNOWLEDGE

    def test_router_with_expander_integration(self):
        """Test: Intégration Router + Expander"""
        router = QueryRouter(use_context_manager=True)
        expander = get_query_expander()

        # Expand puis route
        query = "FCR Ross"
        expanded = expander.expand_query(query)
        result = router.route_query(expanded)

        assert result == QueryType.METRICS


# ==================== Test Runner ====================

def run_phase2_tests():
    """Execute tous les tests Phase 2 et affiche résultats"""
    print("\n" + "="*80)
    print("TESTS END-TO-END PHASE 2")
    print("="*80 + "\n")

    # Run pytest avec verbose output
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-ra",  # Show summary of all tests
        "--color=yes"
    ])

    return exit_code


if __name__ == "__main__":
    exit_code = run_phase2_tests()

    print("\n" + "="*80)
    if exit_code == 0:
        print("TOUS LES TESTS PHASE 2 PASSENT ✅")
    else:
        print(f"CERTAINS TESTS ONT ECHOUE (exit code: {exit_code})")
    print("="*80 + "\n")

    sys.exit(exit_code)

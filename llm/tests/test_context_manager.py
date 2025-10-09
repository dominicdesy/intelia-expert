# -*- coding: utf-8 -*-
"""
test_context_manager.py - Tests pour ContextManager v1.0

Tests de résolution de contexte multi-turn
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from processing.context_manager import ContextManager, ConversationContext


class TestContextManager:
    """Tests pour ContextManager"""

    @pytest.fixture
    def manager(self):
        """Fixture: New ContextManager instance"""
        return ContextManager()

    def test_initialization(self, manager):
        """Test initialization"""
        assert manager is not None
        assert manager.context.breed is None
        assert manager.context.age is None
        assert len(manager.context_history) == 0

    # ===== ENTITY EXTRACTION =====

    def test_extract_breed(self, manager):
        """Test breed extraction"""
        entities = manager.extract_entities("Ross 308 performance")
        assert entities['breed'].lower() == "ross 308"

        entities = manager.extract_entities("Cobb 500 vs Ross 308")
        assert 'cobb 500' in entities['breed'].lower() or 'ross 308' in entities['breed'].lower()

    def test_extract_age(self, manager):
        """Test age extraction"""
        entities = manager.extract_entities("Poids à 35 jours")
        assert entities['age'] == 35

        entities = manager.extract_entities("FCR at 42 days")
        assert entities['age'] == 42

    def test_extract_sex(self, manager):
        """Test sex extraction"""
        entities = manager.extract_entities("Poids mâles")
        assert entities['sex'] == 'male'

        entities = manager.extract_entities("Performance femelles")
        assert entities['sex'] == 'female'

    def test_extract_metric(self, manager):
        """Test metric extraction"""
        entities = manager.extract_entities("Quel est le poids?")
        assert entities['metric'] == 'poids'

        entities = manager.extract_entities("FCR à 35 jours")
        assert entities['metric'] == 'fcr'

    # ===== COREFERENCE DETECTION =====

    def test_detect_coreference_explicit(self, manager):
        """Test explicit coreference patterns"""
        assert manager.is_coreference("Et pour les femelles?") == True
        assert manager.is_coreference("Même chose pour le Hubbard?") == True
        assert manager.is_coreference("À cet âge-là?") == True
        assert manager.is_coreference("Pour cette race?") == True

    def test_detect_coreference_short_query(self, manager):
        """Test coreference detection on short queries"""
        assert manager.is_coreference("Poids?") == True  # Too short
        assert manager.is_coreference("FCR") == True  # Too short
        assert manager.is_coreference("Quel poids?") == True  # No context

    def test_detect_no_coreference(self, manager):
        """Test queries that don't need coreference"""
        assert manager.is_coreference("Quel est le poids Ross 308 à 35 jours?") == False
        assert manager.is_coreference("FCR Cobb 500 at 42 days") == False

    # ===== CONTEXT UPDATE =====

    def test_update_context_simple(self, manager):
        """Test context update from complete query"""
        manager.update_context("Poids Ross 308 à 35 jours")

        assert manager.context.breed == "Ross 308"
        assert manager.context.age == 35
        assert manager.context.metric == 'poids'

    def test_update_context_preserves_previous(self, manager):
        """Test that context preserves previous values"""
        manager.update_context("Ross 308 à 35 jours")
        assert manager.context.breed == "Ross 308"
        assert manager.context.age == 35

        # New query without breed
        manager.update_context("FCR à 42 jours")
        assert manager.context.breed == "Ross 308"  # Preserved
        assert manager.context.age == 42  # Updated
        assert manager.context.metric == 'fcr'  # Updated

    # ===== QUERY EXPANSION =====

    def test_expand_query_with_sex(self, manager):
        """Test query expansion with sex change"""
        # Setup context
        manager.update_context("Poids Ross 308 à 35 jours")

        # Expand incomplete query
        expanded = manager.expand_query("Et pour les femelles?")

        assert 'ross' in expanded.lower() or 'ross 308' in expanded.lower()
        assert 'femelles' in expanded.lower()
        assert '35' in expanded or 'jours' in expanded.lower()

    def test_expand_query_with_breed(self, manager):
        """Test query expansion with breed change"""
        manager.update_context("FCR Ross 308 à 42 jours")

        expanded = manager.expand_query("Même chose pour Cobb 500?")

        assert 'cobb 500' in expanded.lower()
        assert 'fcr' in expanded.lower()
        assert '42' in expanded

    def test_expand_query_no_context(self, manager):
        """Test expansion without context (returns original)"""
        expanded = manager.expand_query("Et pour les femelles?")
        # Should return original or warn
        assert expanded is not None

    def test_expand_complete_query(self, manager):
        """Test that complete queries are not expanded"""
        query = "Quel est le poids Ross 308 à 35 jours?"
        expanded = manager.expand_query(query)
        assert expanded == query  # No expansion needed

    # ===== INTEGRATION TESTS =====

    def test_full_conversation_flow(self, manager):
        """Test complete multi-turn conversation"""
        # Turn 1: Complete query
        manager.update_context("Quel est le poids Ross 308 à 35 jours?")
        assert manager.context.breed == "Ross 308"
        assert manager.context.age == 35
        assert manager.context.metric == 'poids'

        # Turn 2: Coreference (sex change)
        expanded = manager.expand_query("Et pour les femelles?")
        assert 'ross' in expanded.lower() or 'ross 308' in expanded.lower()
        assert 'femelles' in expanded.lower()

        # Turn 3: Coreference (age change)
        manager.update_context(expanded)  # Update from expanded
        expanded2 = manager.expand_query("À 42 jours?")
        assert '42' in expanded2

    def test_context_summary(self, manager):
        """Test context summary"""
        manager.update_context("FCR Ross 308 femelles à 35 jours")

        summary = manager.get_context_summary()
        assert 'Ross 308' in summary or 'ross 308' in summary.lower()
        assert '35' in summary
        assert 'female' in summary.lower() or 'femelle' in summary.lower()
        assert 'fcr' in summary.lower()

    def test_clear_context(self, manager):
        """Test context clearing"""
        manager.update_context("Ross 308 à 35 jours")
        assert manager.context.breed is not None

        manager.clear_context()
        assert manager.context.breed is None
        assert manager.context.age is None
        assert len(manager.context_history) == 0


def run_context_manager_tests():
    """
    Run comprehensive ContextManager tests

    Returns:
        bool: True if all tests pass
    """
    import logging
    logging.basicConfig(level=logging.INFO)

    manager = ContextManager()

    test_cases = [
        # (setup_query, coreference_query, expected_expansion_contains)
        (
            "Poids Ross 308 à 35 jours",
            "Et pour les femelles?",
            ['ross', 'femelles', '35']
        ),
        (
            "FCR Cobb 500 males at 42 days",
            "Même chose pour Hubbard?",
            ['hubbard', 'fcr', '42']
        ),
        (
            "Gain Ross 308 à 28 jours",
            "À 35 jours?",
            ['ross', 'gain', '35']
        ),
    ]

    print("\n" + "="*80)
    print("CONTEXT MANAGER - COMPREHENSIVE TEST SUITE")
    print("="*80 + "\n")

    passed = 0
    failed = 0

    for setup_query, coreference_query, expected_parts in test_cases:
        # Setup context
        manager.clear_context()
        manager.update_context(setup_query)

        # Test expansion
        expanded = manager.expand_query(coreference_query)

        # Verify expected parts
        all_present = all(
            any(part.lower() in expanded.lower() for part in [expected])
            for expected in expected_parts
        )

        status = "PASS" if all_present else "FAIL"
        print(f"{status} | Setup: {setup_query}")
        print(f"       | Coreference: {coreference_query}")
        print(f"       | Expanded: {expanded}")
        print(f"       | Expected parts: {expected_parts}\n")

        if all_present:
            passed += 1
        else:
            failed += 1

    print("="*80)
    print(f"RESULTS: {passed} passed, {failed} failed (Total: {len(test_cases)})")
    print("="*80 + "\n")

    return failed == 0


if __name__ == "__main__":
    # Run comprehensive test
    success = run_context_manager_tests()

    # Or run pytest
    # pytest.main([__file__, "-v"])

    exit(0 if success else 1)

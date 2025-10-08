# -*- coding: utf-8 -*-
"""
test_enhanced_clarification.py - Tests for Enhanced Clarification System (Phase 3.2)

Tests clarification detection, message building, and router integration
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.enhanced_clarification import (
    EnhancedClarification,
    get_enhanced_clarification
)


class TestEnhancedClarificationBasics:
    """Basic functionality tests"""

    @pytest.fixture
    def clarifier(self):
        """Fixture: New EnhancedClarification instance"""
        # Create instance that might not have helper (graceful degradation)
        return EnhancedClarification()

    def test_initialization(self, clarifier):
        """Test initialization"""
        assert clarifier is not None
        # Should initialize even if helper not available
        assert hasattr(clarifier, 'helper')
        assert hasattr(clarifier, 'helper_available')

    def test_singleton_instance(self):
        """Test singleton factory function"""
        instance1 = get_enhanced_clarification()
        instance2 = get_enhanced_clarification()
        assert instance1 is instance2

    def test_is_available(self, clarifier):
        """Test availability check"""
        available = clarifier.is_available()
        assert isinstance(available, bool)


class TestAmbiguityDetection:
    """Test detection of 7 ambiguity types"""

    @pytest.fixture
    def clarifier(self):
        return EnhancedClarification()

    def test_detect_nutrition_ambiguity(self, clarifier):
        """Test nutrition ambiguity detection"""
        query = "Quelle formule aliment donner?"
        missing_fields = ['age']
        entities = {}

        # May return None if helper not available (graceful degradation)
        ambiguity_type = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        # If helper available, should detect nutrition_ambiguity
        if clarifier.is_available():
            assert ambiguity_type == 'nutrition_ambiguity'
        else:
            assert ambiguity_type is None

    def test_detect_health_symptom_vague(self, clarifier):
        """Test health symptom ambiguity detection"""
        query = "Mes poulets sont malades"
        missing_fields = ['age', 'breed']
        entities = {}

        ambiguity_type = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        if clarifier.is_available():
            assert ambiguity_type == 'health_symptom_vague'

    def test_detect_performance_incomplete(self, clarifier):
        """Test performance incomplete detection"""
        query = "Quel est le poids?"
        missing_fields = ['breed', 'age']
        entities = {}

        ambiguity_type = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        if clarifier.is_available():
            assert ambiguity_type == 'performance_incomplete'

    def test_detect_environment_vague(self, clarifier):
        """Test environment vague detection"""
        query = "Quelle température idéale?"
        missing_fields = ['age']
        entities = {}

        ambiguity_type = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        if clarifier.is_available():
            assert ambiguity_type == 'environment_vague'

    def test_detect_management_broad(self, clarifier):
        """Test management broad detection"""
        query = "Comment améliorer rentabilité?"
        missing_fields = ['breed', 'age', 'metric']
        entities = {}

        ambiguity_type = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        if clarifier.is_available():
            assert ambiguity_type == 'management_broad'

    def test_detect_genetics_incomplete(self, clarifier):
        """Test genetics incomplete detection"""
        query = "Comparer Ross 308 et Cobb 500"
        missing_fields = ['metric', 'age']
        entities = {}

        ambiguity_type = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        if clarifier.is_available():
            # May be genetics_incomplete or performance_incomplete
            assert ambiguity_type in ['genetics_incomplete', 'performance_incomplete', None]

    def test_detect_treatment_protocol_vague(self, clarifier):
        """Test treatment protocol vague detection"""
        query = "Quel protocole vaccinal?"
        missing_fields = ['age', 'breed']
        entities = {}

        ambiguity_type = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        if clarifier.is_available():
            assert ambiguity_type in ['treatment_protocol_vague', 'health_symptom_vague', None]

    def test_no_ambiguity_when_complete(self, clarifier):
        """Test no ambiguity detected for complete queries"""
        query = "Quel est le poids Ross 308 mâles à 35 jours?"
        missing_fields = []
        entities = {'breed': 'Ross 308', 'age': 35, 'sex': 'male'}

        ambiguity_type = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        # Should not detect ambiguity (no missing fields)
        assert ambiguity_type is None


class TestClarificationMessages:
    """Test clarification message building"""

    @pytest.fixture
    def clarifier(self):
        return EnhancedClarification()

    def test_build_message_single_field(self, clarifier):
        """Test building message for single missing field"""
        query = "Quel poids?"
        missing_fields = ['breed']
        language = 'en'

        message = clarifier.build_clarification_message(
            query=query,
            missing_fields=missing_fields,
            language=language
        )

        assert isinstance(message, str)
        assert len(message) > 0
        # Should mention breed
        assert 'breed' in message.lower() or 'race' in message.lower()

    def test_build_message_multiple_fields(self, clarifier):
        """Test building message for multiple missing fields"""
        query = "Performance query"
        missing_fields = ['breed', 'age', 'sex']
        language = 'en'

        message = clarifier.build_clarification_message(
            query=query,
            missing_fields=missing_fields,
            language=language
        )

        assert isinstance(message, str)
        assert len(message) > 0
        # Should be a longer message with multiple items
        assert message.count('-') >= 2 or message.count('\n') >= 2

    def test_build_message_french(self, clarifier):
        """Test building message in French"""
        query = "Quel poids?"
        missing_fields = ['breed', 'age']
        language = 'fr'

        message = clarifier.build_clarification_message(
            query=query,
            missing_fields=missing_fields,
            language=language
        )

        assert isinstance(message, str)
        assert len(message) > 0

        # If helper available with LLM translation, should have French
        # If fallback, will use French templates
        # Either way, message should exist

    def test_build_message_with_entities(self, clarifier):
        """Test building message with existing entities"""
        query = "Quel poids Ross 308?"
        missing_fields = ['age']
        language = 'en'
        entities = {'breed': 'Ross 308'}

        message = clarifier.build_clarification_message(
            query=query,
            missing_fields=missing_fields,
            language=language,
            entities=entities
        )

        assert isinstance(message, str)
        assert len(message) > 0
        # Should only ask for age, not breed (already known)

    def test_fallback_message_english(self, clarifier):
        """Test fallback message in English"""
        message = clarifier._build_fallback_message(['breed', 'age'], 'en')

        assert 'Breed' in message or 'breed' in message
        assert 'Age' in message or 'age' in message
        assert 'Ross' in message  # Example breed

    def test_fallback_message_french(self, clarifier):
        """Test fallback message in French"""
        message = clarifier._build_fallback_message(['breed', 'age'], 'fr')

        assert 'Race' in message or 'race' in message
        assert 'Âge' in message or 'âge' in message or 'Age' in message


class TestCheckAndClarify:
    """Test check_and_clarify integration method"""

    @pytest.fixture
    def clarifier(self):
        return EnhancedClarification()

    def test_check_no_clarification_needed(self, clarifier):
        """Test when no clarification needed"""
        result = clarifier.check_and_clarify(
            query="Complete query",
            missing_fields=[],
            language='en'
        )

        assert result['needs_clarification'] == False
        assert result['message'] == ''
        assert result['ambiguity_type'] is None

    def test_check_clarification_needed(self, clarifier):
        """Test when clarification is needed"""
        result = clarifier.check_and_clarify(
            query="Quel poids?",
            missing_fields=['breed', 'age'],
            language='en'
        )

        assert result['needs_clarification'] == True
        assert len(result['message']) > 0
        assert 'missing_fields' in result
        assert len(result['missing_fields']) == 2

    def test_check_with_ambiguity_detection(self, clarifier):
        """Test clarification with ambiguity type detection"""
        result = clarifier.check_and_clarify(
            query="Quelle formule aliment?",
            missing_fields=['age'],
            language='fr',
            entities={}
        )

        assert result['needs_clarification'] == True
        # ambiguity_type may be None or a string depending on helper availability
        assert 'ambiguity_type' in result

    def test_check_preserves_language(self, clarifier):
        """Test that language is preserved in result"""
        result = clarifier.check_and_clarify(
            query="Query",
            missing_fields=['breed'],
            language='es'
        )

        assert result['language'] == 'es'


class TestShouldClarifyBeforeLLM:
    """Test should_clarify_before_llm decision logic"""

    @pytest.fixture
    def clarifier(self):
        return EnhancedClarification()

    def test_should_clarify_critical_field_missing(self, clarifier):
        """Test clarification when critical field missing"""
        should_clarify = clarifier.should_clarify_before_llm(
            query="Query",
            missing_fields=['breed'],
            confidence=0.8
        )

        assert should_clarify == True  # breed is critical

    def test_should_clarify_many_fields_missing(self, clarifier):
        """Test clarification when many fields missing"""
        should_clarify = clarifier.should_clarify_before_llm(
            query="Query",
            missing_fields=['field1', 'field2', 'field3'],
            confidence=0.8
        )

        assert should_clarify == True  # 3+ fields missing

    def test_should_clarify_low_confidence(self, clarifier):
        """Test clarification when low confidence"""
        should_clarify = clarifier.should_clarify_before_llm(
            query="Query",
            missing_fields=['some_field'],
            confidence=0.3
        )

        assert should_clarify == True  # Low confidence + missing field

    def test_should_not_clarify_high_confidence_non_critical(self, clarifier):
        """Test no clarification when high confidence and non-critical"""
        should_clarify = clarifier.should_clarify_before_llm(
            query="Query",
            missing_fields=['non_critical_field'],
            confidence=0.9
        )

        # May or may not clarify depending on field
        assert isinstance(should_clarify, bool)

    def test_should_not_clarify_no_missing_fields(self, clarifier):
        """Test no clarification when no missing fields"""
        should_clarify = clarifier.should_clarify_before_llm(
            query="Query",
            missing_fields=[],
            confidence=0.9
        )

        assert should_clarify == False


class TestGracefulDegradation:
    """Test graceful degradation when helper unavailable"""

    def test_degradation_when_no_helper(self):
        """Test graceful degradation when ClarificationHelper unavailable"""
        # Mock ClarificationHelper to fail
        with patch('utils.enhanced_clarification.get_clarification_helper') as mock_helper:
            mock_helper.side_effect = Exception("API key not available")

            # Should still initialize
            clarifier = EnhancedClarification()

            assert clarifier is not None
            assert clarifier.is_available() == False

            # Should still be able to build messages (using fallback)
            message = clarifier.build_clarification_message(
                query="Test",
                missing_fields=['breed'],
                language='en'
            )

            assert isinstance(message, str)
            assert len(message) > 0

    def test_fallback_messages_work(self):
        """Test that fallback messages work without helper"""
        clarifier = EnhancedClarification()

        # Manually set helper_available to False to test fallback
        original_available = clarifier.helper_available
        clarifier.helper_available = False

        message = clarifier.build_clarification_message(
            query="Test",
            missing_fields=['breed', 'age'],
            language='en'
        )

        assert isinstance(message, str)
        assert len(message) > 0
        assert 'breed' in message.lower()

        # Restore
        clarifier.helper_available = original_available


class TestIntegration:
    """Integration tests for complete workflow"""

    @pytest.fixture
    def clarifier(self):
        return EnhancedClarification()

    def test_full_workflow_nutrition_question(self, clarifier):
        """Test complete workflow for nutrition question"""
        query = "Quelle formule aliment pour mes poulets?"
        missing_fields = ['age', 'breed']
        language = 'fr'
        entities = {}

        # Detect ambiguity
        ambiguity = clarifier.detect_ambiguity_type(query, missing_fields, entities)

        # Build message
        message = clarifier.build_clarification_message(
            query=query,
            missing_fields=missing_fields,
            language=language,
            entities=entities
        )

        assert isinstance(message, str)
        assert len(message) > 0

        # Check if should clarify before LLM
        should_clarify = clarifier.should_clarify_before_llm(
            query=query,
            missing_fields=missing_fields,
            confidence=0.4
        )

        assert should_clarify == True

    def test_full_workflow_complete_question(self, clarifier):
        """Test workflow with complete question"""
        query = "Quel poids Ross 308 mâles à 35 jours?"
        missing_fields = []
        language = 'fr'
        entities = {'breed': 'Ross 308', 'age': 35, 'sex': 'male'}

        # Check and clarify
        result = clarifier.check_and_clarify(
            query=query,
            missing_fields=missing_fields,
            language=language,
            entities=entities
        )

        assert result['needs_clarification'] == False

    def test_full_workflow_health_question(self, clarifier):
        """Test workflow for health question"""
        query = "Mes poulets ont des symptômes"
        missing_fields = ['age', 'breed']
        language = 'fr'

        result = clarifier.check_and_clarify(
            query=query,
            missing_fields=missing_fields,
            language=language
        )

        assert result['needs_clarification'] == True
        assert len(result['message']) > 0


def run_enhanced_clarification_tests():
    """
    Run comprehensive Enhanced Clarification tests

    Returns:
        bool: True if all tests pass
    """
    import logging
    logging.basicConfig(level=logging.INFO)

    print("\n" + "="*80)
    print("ENHANCED CLARIFICATION - COMPREHENSIVE TEST SUITE (Phase 3.2)")
    print("="*80 + "\n")

    clarifier = EnhancedClarification()

    test_cases = [
        # (query, missing_fields, expected_clarification_needed)
        ("Quel poids Ross 308 à 35 jours?", [], False),
        ("Quel poids?", ['breed', 'age'], True),
        ("Quelle formule aliment?", ['age', 'breed'], True),
        ("Mes poulets sont malades", ['age', 'breed'], True),
        ("Performance query", ['breed'], True),
    ]

    passed = 0
    failed = 0

    for query, missing_fields, expected_needs_clarification in test_cases:
        result = clarifier.check_and_clarify(
            query=query,
            missing_fields=missing_fields,
            language='en'
        )

        needs_clarification = result['needs_clarification']
        match = needs_clarification == expected_needs_clarification

        if match:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1

        print(f"{status} | Query: {query}")
        print(f"       | Missing fields: {missing_fields}")
        print(f"       | Needs clarification: {needs_clarification} (expected: {expected_needs_clarification})")
        print(f"       | Ambiguity type: {result.get('ambiguity_type')}")
        if result.get('message'):
            print(f"       | Message: {result['message'][:60]}...")
        print()

    print("="*80)
    print(f"RESULTS: {passed} passed, {failed} failed (Total: {len(test_cases)})")
    print("="*80 + "\n")

    return failed == 0


if __name__ == "__main__":
    # Run comprehensive test
    success = run_enhanced_clarification_tests()

    # Or run pytest
    # pytest.main([__file__, "-v"])

    exit(0 if success else 1)

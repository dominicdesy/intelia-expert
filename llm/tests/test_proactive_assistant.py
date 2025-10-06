# -*- coding: utf-8 -*-
"""
test_proactive_assistant.py - Tests for Proactive Assistant

Tests the context-aware follow-up question generation system
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generation.proactive_assistant import ProactiveAssistant, AssistanceContext


def test_performance_issue_context():
    """Test follow-up for performance-related queries"""

    print("\n" + "=" * 70)
    print("TEST 1: PERFORMANCE ISSUE CONTEXT")
    print("=" * 70)

    assistant = ProactiveAssistant(default_language="fr")

    # Test case: Weight query
    query = "Quel poids pour Ross 308 à 35 jours ?"
    response = "Le poids cible est 2.2-2.4 kg."
    entities = {"metric_type": "body_weight", "breed": "ross 308", "age_days": 35}

    follow_up = assistant.generate_follow_up(
        query=query, response=response, entities=entities, language="fr"
    )

    print(f"\nQuery: {query}")
    print(f"Response: {response}")
    print(f"Follow-up: {follow_up}")

    assert follow_up, "Follow-up should be generated"
    assert "poids" in follow_up.lower(), "Follow-up should mention 'poids'"
    assert "?" in follow_up, "Follow-up should be a question"

    print("\nOK - Performance issue context: PASS")


def test_health_concern_context():
    """Test follow-up for health-related queries"""

    print("\n" + "=" * 70)
    print("TEST 2: HEALTH CONCERN CONTEXT")
    print("=" * 70)

    assistant = ProactiveAssistant(default_language="en")

    # Test case: Mortality query
    query = "What is the mortality rate for Cobb 500?"
    response = "The mortality rate is typically 3-5% at 42 days."
    intent_result = {"domain": "health", "query_type": "standard"}
    entities = {"metric_type": "mortality"}

    follow_up = assistant.generate_follow_up(
        query=query,
        response=response,
        intent_result=intent_result,
        entities=entities,
        language="en",
    )

    print(f"\nQuery: {query}")
    print(f"Response: {response}")
    print(f"Follow-up: {follow_up}")

    assert follow_up, "Follow-up should be generated"
    assert "?" in follow_up, "Follow-up should be a question"

    print("\nOK - Health concern context: PASS")


def test_comparison_context():
    """Test follow-up for comparison queries"""

    print("\n" + "=" * 70)
    print("TEST 3: COMPARISON CONTEXT")
    print("=" * 70)

    assistant = ProactiveAssistant(default_language="fr")

    # Test case: Comparison query
    query = "Compare Ross 308 et Cobb 500 à 35 jours"
    response = "Ross 308: 2.3 kg, Cobb 500: 2.4 kg. Cobb 500 est légèrement plus lourd."
    intent_result = {"query_type": "comparative"}
    entities = {"breed": ["ross 308", "cobb 500"], "age_days": 35}

    follow_up = assistant.generate_follow_up(
        query=query,
        response=response,
        intent_result=intent_result,
        entities=entities,
        language="fr",
    )

    print(f"\nQuery: {query}")
    print(f"Response: {response}")
    print(f"Follow-up: {follow_up}")

    assert follow_up, "Follow-up should be generated"
    assert "?" in follow_up, "Follow-up should be a question"

    print("\nOK - Comparison context: PASS")


def test_optimization_context():
    """Test follow-up for optimization queries"""

    print("\n" + "=" * 70)
    print("TEST 4: OPTIMIZATION CONTEXT")
    print("=" * 70)

    assistant = ProactiveAssistant(default_language="fr")

    # Test case: Optimization query
    query = "Comment améliorer le FCR de mes poulets ?"
    response = "Pour améliorer le FCR, optimisez la formulation alimentaire et l'environnement."
    entities = {"metric_type": "feed_conversion_ratio"}

    follow_up = assistant.generate_follow_up(
        query=query, response=response, entities=entities, language="fr"
    )

    print(f"\nQuery: {query}")
    print(f"Response: {response}")
    print(f"Follow-up: {follow_up}")

    assert follow_up, "Follow-up should be generated"
    assert "?" in follow_up, "Follow-up should be a question"

    print("\nOK - Optimization context: PASS")


def test_multilingual_support():
    """Test follow-up in different languages"""

    print("\n" + "=" * 70)
    print("TEST 5: MULTILINGUAL SUPPORT")
    print("=" * 70)

    assistant = ProactiveAssistant()

    query = "Quel poids pour Ross 308 ?"
    response = "2.3 kg à 35 jours."
    entities = {"metric_type": "body_weight"}

    # French
    follow_up_fr = assistant.generate_follow_up(
        query=query, response=response, entities=entities, language="fr"
    )
    print(f"\nFrench follow-up: {follow_up_fr}")
    assert "poids" in follow_up_fr.lower()

    # English
    follow_up_en = assistant.generate_follow_up(
        query=query, response=response, entities=entities, language="en"
    )
    print(f"English follow-up: {follow_up_en}")
    assert "weight" in follow_up_en.lower()

    # Spanish
    follow_up_es = assistant.generate_follow_up(
        query=query, response=response, entities=entities, language="es"
    )
    print(f"Spanish follow-up: {follow_up_es}")
    assert "peso" in follow_up_es.lower()

    print("\nOK - Multilingual support: PASS")


def test_context_identification():
    """Test correct context identification"""

    print("\n" + "=" * 70)
    print("TEST 6: CONTEXT IDENTIFICATION")
    print("=" * 70)

    assistant = ProactiveAssistant()

    test_cases = [
        {
            "query": "Quel poids pour Ross 308 ?",
            "expected": AssistanceContext.PERFORMANCE_ISSUE,
        },
        {
            "query": "Symptômes de la coccidiose",
            "expected": AssistanceContext.HEALTH_CONCERN,
        },
        {
            "query": "Compare Ross 308 vs Cobb 500",
            "expected": AssistanceContext.COMPARISON,
        },
        {
            "query": "Comment améliorer le FCR ?",
            "expected": AssistanceContext.OPTIMIZATION,
        },
        {
            "query": "Planifier ma prochaine bande",
            "expected": AssistanceContext.PLANNING,
        },
    ]

    for i, test in enumerate(test_cases, 1):
        context = assistant._identify_context(
            query=test["query"],
            response="",
            intent_result=None,
            entities=None,
        )

        print(f"\nTest {i}: '{test['query']}'")
        print(f"  Expected: {test['expected'].value}")
        print(f"  Got: {context.value}")
        print(f"  Status: {'OK - PASS' if context == test['expected'] else 'FAIL - FAIL'}")

        assert context == test["expected"], f"Context mismatch for: {test['query']}"

    print("\nOK - Context identification: PASS")


if __name__ == "__main__":
    print("\nPROACTIVE ASSISTANT TEST SUITE")
    print("=" * 70)

    try:
        test_performance_issue_context()
        test_health_concern_context()
        test_comparison_context()
        test_optimization_context()
        test_multilingual_support()
        test_context_identification()

        print("\n" + "=" * 70)
        print("OK - ALL TESTS PASSED")
        print("=" * 70)

    except AssertionError as e:
        print(f"\nFAIL - TEST FAILED: {e}")
        import traceback

        traceback.print_exc()

    except Exception as e:
        print(f"\nFAIL - ERROR: {e}")
        import traceback

        traceback.print_exc()

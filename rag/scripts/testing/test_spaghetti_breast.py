# -*- coding: utf-8 -*-
"""
Test for Spaghetti Breast Detection - The Original Problem

This test verifies that "What is Spaghetti breast?" is now correctly detected
as a poultry-related question (GENERAL_POULTRY) instead of OUT_OF_DOMAIN.

Original Issue:
- Query: "What is Spaghetti breast?"
- Old behavior: OUT_OF_DOMAIN (term not in vocabulary)
- New behavior: GENERAL_POULTRY (detected via AGROVOC Level 2 manual terms)
"""

import logging
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from processing.intent_processor import IntentProcessor
from processing.intent_types import IntentType

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_spaghetti_breast():
    """Test that Spaghetti breast is now detected as poultry-related"""

    print("\n" + "=" * 80)
    print("TEST SPAGHETTI BREAST DETECTION - Original Problem")
    print("=" * 80)

    # Initialize IntentProcessor
    try:
        processor = IntentProcessor()
    except Exception as e:
        print(f"[ERROR] Failed to initialize IntentProcessor: {e}")
        return False

    # Test cases for modern meat quality defects
    test_cases = [
        # Original problem case
        ("What is Spaghetti breast?", IntentType.GENERAL_POULTRY, "en"),
        ("What is spaghetti breast?", IntentType.GENERAL_POULTRY, "en"),  # lowercase
        # Other modern defects
        ("What is white striping?", IntentType.GENERAL_POULTRY, "en"),
        ("What is wooden breast?", IntentType.GENERAL_POULTRY, "en"),
        ("What is deep pectoral myopathy?", IntentType.GENERAL_POULTRY, "en"),
        # French versions
        ("Qu'est-ce que la poitrine spaghetti?", IntentType.GENERAL_POULTRY, "fr"),
        ("Qu'est-ce que les stries blanches?", IntentType.GENERAL_POULTRY, "fr"),
        # Spanish versions
        ("¿Qué es la pechuga espagueti?", IntentType.GENERAL_POULTRY, "es"),
        # Dutch version
        ("Wat is spaghetti borst?", IntentType.GENERAL_POULTRY, "nl"),
        # Traditional diseases (should also work via AGROVOC Level 1)
        ("What is Newcastle disease?", IntentType.GENERAL_POULTRY, "en"),
        ("What is Marek's disease?", IntentType.GENERAL_POULTRY, "en"),
        # Non-poultry queries (should be OUT_OF_DOMAIN)
        (
            "What is spaghetti?",
            IntentType.OUT_OF_DOMAIN,
            "en",
        ),  # Just spaghetti, not "spaghetti breast"
        ("What is artificial intelligence?", IntentType.OUT_OF_DOMAIN, "en"),
    ]

    results = {"correct": 0, "incorrect": 0, "total": len(test_cases)}

    print("\nTest Results:\n")

    for query, expected_intent, language in test_cases:
        result = processor.process_query(query)
        detected_intent = result.intent_type

        is_correct = detected_intent == expected_intent

        status = "[PASS]" if is_correct else "[FAIL]"

        print(f"{status} Query: {query}")
        print(f"      Language: {language}")
        print(f"      Expected: {expected_intent.value}, Got: {detected_intent.value}")
        print(f"      Confidence: {result.confidence:.2f}")
        print()

        if is_correct:
            results["correct"] += 1
        else:
            results["incorrect"] += 1

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests: {results['total']}")
    print(f"Correct: {results['correct']}")
    print(f"Incorrect: {results['incorrect']}")
    print(f"Accuracy: {results['correct'] / results['total'] * 100:.1f}%")

    if results["correct"] == results["total"]:
        print("\n[SUCCESS] All tests passed!")
        print("\nSpaghetti breast is now correctly detected as a poultry term!")
        return True
    else:
        print(
            f"\n[PARTIAL SUCCESS] {results['correct']}/{results['total']} tests passed"
        )
        return False


if __name__ == "__main__":
    success = test_spaghetti_breast()
    sys.exit(0 if success else 1)

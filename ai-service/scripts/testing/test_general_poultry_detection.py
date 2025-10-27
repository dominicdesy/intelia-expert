# -*- coding: utf-8 -*-
"""
Test pour la détection de termes généraux d'aviculture

Test case problématique:
- Query: "Is it safe to use artificial intelligence technologies to raise poultry?"
- Ancien comportement: Détecté comme OUT_OF_DOMAIN (pas d'entités spécifiques) ❌
- Nouveau comportement: Détecté comme GENERAL_POULTRY (contient "raise", "poultry") ✅
"""

import logging
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from processing.intent_processor import IntentProcessor
from processing.intent_types import IntentType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_general_poultry_detection():
    """Test de détection de termes généraux d'aviculture"""

    print("\n" + "="*80)
    print("TEST DE DÉTECTION DE TERMES GÉNÉRAUX D'AVICULTURE")
    print("="*80)

    # Initialize IntentProcessor
    try:
        processor = IntentProcessor()
    except Exception as e:
        print(f"[ERROR] Failed to initialize IntentProcessor: {e}")
        return False

    # Test cases
    test_cases = [
        # General poultry queries (should be GENERAL_POULTRY, NOT OUT_OF_DOMAIN)
        ("Is it safe to use artificial intelligence technologies to raise poultry?", IntentType.GENERAL_POULTRY, "en"),
        ("How to improve chicken farming?", IntentType.GENERAL_POULTRY, "en"),
        ("What are the benefits of free-range poultry production?", IntentType.GENERAL_POULTRY, "en"),
        ("Can I use solar panels for my chicken farm?", IntentType.GENERAL_POULTRY, "en"),
        ("Is organic feed better for broilers?", IntentType.GENERAL_POULTRY, "en"),

        # French queries
        ("Comment améliorer l'élevage de poulets?", IntentType.GENERAL_POULTRY, "fr"),
        ("Quelle est la meilleure façon d'élever des volailles?", IntentType.GENERAL_POULTRY, "fr"),

        # OUT_OF_DOMAIN queries (no poultry terms)
        ("What is artificial intelligence?", IntentType.OUT_OF_DOMAIN, "en"),
        ("How to make a cake?", IntentType.OUT_OF_DOMAIN, "en"),
        ("What is the weather today?", IntentType.OUT_OF_DOMAIN, "en"),
    ]

    results = {"correct": 0, "incorrect": 0, "total": len(test_cases)}

    print("\nTest Results:\n")

    for query, expected_intent, language in test_cases:
        result = processor.process_query(query)
        detected_intent = result.intent_type

        is_correct = detected_intent == expected_intent

        status = "[PASS]" if is_correct else "[FAIL]"

        print(f"{status} Query: {query}")
        print(f"      Expected: {expected_intent.value}, Got: {detected_intent.value}")
        print(f"      Confidence: {result.confidence:.2f}")
        print()

        if is_correct:
            results["correct"] += 1
        else:
            results["incorrect"] += 1

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total tests: {results['total']}")
    print(f"Correct: {results['correct']}")
    print(f"Incorrect: {results['incorrect']}")
    print(f"Accuracy: {results['correct'] / results['total'] * 100:.1f}%")

    if results['correct'] == results['total']:
        print("\n[SUCCESS] All tests passed!")
        return True
    else:
        print(f"\n[FAIL] {results['incorrect']} tests failed")
        return False


if __name__ == "__main__":
    success = test_general_poultry_detection()
    sys.exit(0 if success else 1)

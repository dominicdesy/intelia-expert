# -*- coding: utf-8 -*-
"""
Test pour le fix de détection de langue avec termes techniques latins

Test case problématique:
- Query: "Is in ovo vaccination safe?" (anglais)
- Ancien comportement: Détecté comme italien (à cause de "in ovo")
- Nouveau comportement: Détecté comme anglais (grâce aux patterns grammaticaux)
"""

import logging
from utils.language_detection import detect_language_enhanced

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_language_detection():
    """Test de détection de langue avec termes techniques"""

    print("\n" + "=" * 80)
    print("TEST DE DÉTECTION DE LANGUE - FIX TERMES TECHNIQUES")
    print("=" * 80)

    # Test cases with technical Latin/international terms
    test_cases = [
        # English queries with Latin terms
        ("Is in ovo vaccination safe?", "en"),
        ("What is in ovo injection?", "en"),
        ("How to perform in ovo vaccination?", "en"),
        ("Is Newcastle disease dangerous?", "en"),
        ("What are the symptoms of coccidiosis?", "en"),
        ("Can I use ivermectin for mites?", "en"),
        # French queries
        ("Quelle est la vaccination in ovo?", "fr"),
        ("Comment faire la vaccination in ovo?", "fr"),
        ("Quel est le poids d'un Ross 308?", "fr"),
        ("La maladie de Newcastle est-elle dangereuse?", "fr"),
        # Spanish queries
        ("¿Qué es la vacunación in ovo?", "es"),
        ("¿Cómo realizar la vacunación in ovo?", "es"),
        ("¿Cuál es el peso de un Ross 308?", "es"),
        # Italian queries (should still be detected as Italian)
        ("Cos'è la vaccinazione in ovo?", "it"),
        ("Come si fa la vaccinazione in ovo?", "it"),
        ("Qual è il peso di un Ross 308?", "it"),
    ]

    results = {"correct": 0, "incorrect": 0, "total": len(test_cases)}

    print("\nTest Results:\n")

    for query, expected_lang in test_cases:
        result = detect_language_enhanced(query)
        detected_lang = result.language
        is_correct = detected_lang == expected_lang

        status = "[PASS]" if is_correct else "[FAIL]"

        print(f"{status} Query: {query}")
        print(f"      Expected: {expected_lang}, Got: {detected_lang}")
        print(f"      Confidence: {result.confidence:.2f}, Source: {result.source}")
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
        return True
    else:
        print(f"\n[FAIL] {results['incorrect']} tests failed")
        return False


if __name__ == "__main__":
    success = test_language_detection()
    exit(0 if success else 1)

# -*- coding: utf-8 -*-
"""
Test AGROVOC Service - Hybrid 3-Level Poultry Term Detection

Tests:
1. AGROVOC cache terms (Level 1)
2. Manual terms for nl, id (Level 2)
3. Modern meat quality defects (Level 2)
4. Universal fallback (Level 3)
5. Query detection (multi-word terms)
"""

import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.agrovoc_service import AGROVOCService


def test_agrovoc_service():
    """Test AGROVOC service with all 3 levels"""

    print("\n" + "=" * 80)
    print("TEST AGROVOC SERVICE - 3-LEVEL POULTRY TERM DETECTION")
    print("=" * 80)

    # Initialize service
    try:
        agrovoc = AGROVOCService()
    except Exception as e:
        print(f"[ERROR] Failed to initialize AGROVOCService: {e}")
        return False

    # Get statistics
    stats = agrovoc.get_stats()
    print(f"\nService Statistics:")
    print(f"  AGROVOC cache: {stats['agrovoc_terms']:,} terms")
    print(f"  Manual terms: {stats['manual_terms']:,} terms")
    print(f"  Universal fallback: {stats['universal_terms']:,} terms")
    print(f"  Total: {stats['total_terms']:,} terms")
    print(f"\nAGROVOC languages: {', '.join(stats['agrovoc_languages'])}")
    print(f"Manual languages: {', '.join(stats['manual_languages'])}")

    print("\n" + "=" * 80)
    print("TEST CASES")
    print("=" * 80)

    test_cases = [
        # Level 1: AGROVOC cache terms (should be True)
        ("chicken", "en", True, "AGROVOC - English"),
        ("poulet", "fr", True, "AGROVOC - French"),
        ("pollo", "es", True, "AGROVOC - Spanish"),
        ("hähnchen", "de", True, "AGROVOC - German"),
        ("pollame", "it", True, "AGROVOC - Italian"),

        # Level 2: Manual terms - Dutch (nl) and Indonesian (id)
        ("pluimvee", "nl", True, "Manual - Dutch poultry"),
        ("kip", "nl", True, "Manual - Dutch chicken"),
        ("ayam", "id", True, "Manual - Indonesian chicken"),
        ("unggas", "id", True, "Manual - Indonesian poultry"),

        # Level 2: Modern meat quality defects (not in AGROVOC)
        ("spaghetti breast", "en", True, "Manual - Modern defect (EN)"),
        ("white striping", "en", True, "Manual - Modern defect (EN)"),
        ("wooden breast", "en", True, "Manual - Modern defect (EN)"),
        ("poitrine spaghetti", "fr", True, "Manual - Modern defect (FR)"),
        ("pechuga espagueti", "es", True, "Manual - Modern defect (ES)"),
        ("spaghetti borst", "nl", True, "Manual - Modern defect (NL)"),

        # Level 3: Universal fallback
        ("broiler", "en", True, "Universal - English"),
        ("volaille", "fr", True, "Universal - French"),
        ("ave", "es", True, "Universal - Spanish"),

        # Negative cases (should be False)
        ("artificial intelligence", "en", False, "Not poultry"),
        ("spaghetti", "en", False, "Partial match not enough"),
        ("intelligence artificielle", "fr", False, "Not poultry (FR)"),
        ("pizza", "it", False, "Not poultry (IT)"),
    ]

    results = {"correct": 0, "incorrect": 0, "total": len(test_cases)}

    for term, language, expected, description in test_cases:
        result = agrovoc.is_poultry_term(term, language)
        is_correct = result == expected

        status = "[PASS]" if is_correct else "[FAIL]"
        result_str = "True" if result else "False"
        expected_str = "True" if expected else "False"

        print(f"{status} {description}")
        print(f"      Term: '{term}' ({language})")
        print(f"      Expected: {expected_str}, Got: {result_str}")
        print()

        if is_correct:
            results["correct"] += 1
        else:
            results["incorrect"] += 1

    # Test query detection
    print("=" * 80)
    print("QUERY DETECTION TESTS")
    print("=" * 80)

    query_tests = [
        ("What is Spaghetti breast?", "en", True, "Modern defect in question"),
        ("Is it safe to use AI to raise poultry?", "en", True, "General poultry question"),
        ("How to improve chicken farming?", "en", True, "General farming question"),
        ("What is artificial intelligence?", "en", False, "Non-poultry question"),
        ("Quelle est la poitrine spaghetti?", "fr", True, "French modern defect"),
        ("Comment améliorer l'élevage de poulets?", "fr", True, "French poultry question"),
    ]

    for query, language, expected, description in query_tests:
        result = agrovoc.detect_poultry_terms_in_query(query, language)
        is_correct = result == expected

        status = "[PASS]" if is_correct else "[FAIL]"
        result_str = "Detected" if result else "Not detected"
        expected_str = "Expected" if expected else "Not expected"

        print(f"{status} {description}")
        print(f"      Query: '{query}'")
        print(f"      {expected_str}, Got: {result_str}")
        print()

        if is_correct:
            results["correct"] += 1
        else:
            results["incorrect"] += 1

    results["total"] = len(test_cases) + len(query_tests)

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests: {results['total']}")
    print(f"Correct: {results['correct']}")
    print(f"Incorrect: {results['incorrect']}")
    print(f"Accuracy: {results['correct'] / results['total'] * 100:.1f}%")

    if results['correct'] == results['total']:
        print("\n[SUCCESS] All tests passed!")
        return True
    else:
        print(f"\n[WARNING] {results['incorrect']} tests failed")
        return False


if __name__ == "__main__":
    success = test_agrovoc_service()
    sys.exit(0 if success else 1)

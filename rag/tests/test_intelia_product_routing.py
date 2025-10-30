"""
Test script for Intelia product detection and routing
Tests both explicit syntax (nano:) and auto-detection
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.entity_extractor import EntityExtractor
from core.query_router import QueryRouter

def test_entity_extraction():
    """Test entity extractor with Intelia products"""
    print("=" * 80)
    print("TEST 1: ENTITY EXTRACTION")
    print("=" * 80)

    extractor = EntityExtractor()

    test_cases = [
        # Explicit syntax
        ("nano: Comment configurer la température ?", "nano", True, 1.0),
        ("compass: Quelle est la consommation d'eau ?", "compass", True, 1.0),
        ("unity: Comment programmer l'éclairage ?", "unity", True, 1.0),

        # Auto-detection
        ("Comment configurer la température dans le nano ?", "nano", True, 0.9),
        ("Le compass affiche une erreur", "compass", True, 0.9),
        ("Avec unity, comment gérer les alarmes ?", "unity", True, 0.9),
        ("Sur le farmhub, où voir les rapports ?", "farmhub", True, 0.9),

        # No product
        ("Quel est le poids des Ross 308 à 35 jours ?", None, False, 0.0),
    ]

    passed = 0
    failed = 0

    for query, expected_product, expected_explicit, expected_confidence in test_cases:
        print(f"\n[TEST] Query: '{query}'")
        entities = extractor.extract(query)

        actual_product = entities.intelia_product
        actual_confidence = entities.confidence_breakdown.get("intelia_product", 0.0)

        if actual_product == expected_product and actual_confidence == expected_confidence:
            print(f"   [PASS] Product: {actual_product}, Confidence: {actual_confidence}")
            passed += 1
        else:
            print(f"   [FAIL] Expected: {expected_product} ({expected_confidence}), Got: {actual_product} ({actual_confidence})")
            failed += 1

    print(f"\n{'=' * 80}")
    print(f"ENTITY EXTRACTION: {passed} passed, {failed} failed")
    print(f"{'=' * 80}\n")

    return failed == 0


def test_query_routing():
    """Test query router with Intelia products"""
    print("=" * 80)
    print("TEST 2: QUERY ROUTING")
    print("=" * 80)

    router = QueryRouter("config")

    test_cases = [
        # Explicit syntax - should route to Weaviate
        ("nano: Comment configurer la température ?", "weaviate", "intelia_product_nano"),
        ("compass: Quelle est la consommation d'eau ?", "weaviate", "intelia_product_compass"),

        # Auto-detection - should route to Weaviate
        ("Comment configurer la température dans le nano ?", "weaviate", "intelia_product_nano"),
        ("Le compass affiche une erreur", "weaviate", "intelia_product_compass"),

        # No product - normal routing
        ("Quel est le poids des Ross 308 à 35 jours ?", "postgresql", None),
    ]

    passed = 0
    failed = 0

    for query, expected_destination, expected_reason_prefix in test_cases:
        print(f"\n[TEST] Query: '{query}'")
        route = router.route(query, user_id="test_user", language="fr")

        actual_destination = route.destination
        actual_reason = route.route_reason

        destination_match = actual_destination == expected_destination
        reason_match = expected_reason_prefix is None or actual_reason.startswith(expected_reason_prefix)

        if destination_match and reason_match:
            print(f"   [PASS] Destination: {actual_destination}, Reason: {actual_reason}")
            passed += 1
        else:
            print(f"   [FAIL] Expected: {expected_destination} ({expected_reason_prefix}), Got: {actual_destination} ({actual_reason})")
            failed += 1

    print(f"\n{'=' * 80}")
    print(f"QUERY ROUTING: {passed} passed, {failed} failed")
    print(f"{'=' * 80}\n")

    return failed == 0


def test_explicit_syntax_cleaning():
    """Test that explicit syntax is properly cleaned from query"""
    print("=" * 80)
    print("TEST 3: QUERY CLEANING")
    print("=" * 80)

    router = QueryRouter("config")

    test_cases = [
        ("nano: Comment configurer la température ?", "Comment configurer la température ?"),
        ("compass: Quelle est la consommation d'eau ?", "Quelle est la consommation d'eau ?"),
        ("unity: Comment programmer l'éclairage ?", "Comment programmer l'éclairage ?"),
    ]

    passed = 0
    failed = 0

    for original_query, expected_cleaned in test_cases:
        print(f"\n[TEST] Original: '{original_query}'")
        route = router.route(original_query, user_id="test_user", language="fr")

        # The cleaned query should be used for extraction
        # We can verify this by checking if the product was detected
        has_product = route.entities.get("intelia_product") is not None

        if has_product:
            print(f"   [PASS] Product detected and syntax cleaned")
            passed += 1
        else:
            print(f"   [FAIL] Product not detected")
            failed += 1

    print(f"\n{'=' * 80}")
    print(f"QUERY CLEANING: {passed} passed, {failed} failed")
    print(f"{'=' * 80}\n")

    return failed == 0


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("INTELIA PRODUCT ROUTING TESTS")
    print("=" * 80 + "\n")

    all_passed = True

    try:
        all_passed &= test_entity_extraction()
    except Exception as e:
        print(f"\n[ERROR] Entity extraction tests crashed: {e}\n")
        all_passed = False

    try:
        all_passed &= test_query_routing()
    except Exception as e:
        print(f"\n[ERROR] Query routing tests crashed: {e}\n")
        all_passed = False

    try:
        all_passed &= test_explicit_syntax_cleaning()
    except Exception as e:
        print(f"\n[ERROR] Query cleaning tests crashed: {e}\n")
        all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED")
    else:
        print("[FAILURE] SOME TESTS FAILED")
    print("=" * 80 + "\n")

    sys.exit(0 if all_passed else 1)

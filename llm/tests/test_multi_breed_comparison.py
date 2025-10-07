# -*- coding: utf-8 -*-
"""
test_multi_breed_comparison.py - Tests pour comparaisons multi-races

Tests le nouveau système de détection et extraction de comparaisons:
1. "Compare Ross 308 vs Cobb 500 à 35 jours" → comparative, 2 breeds
2. "Ross 308 et Cobb 500 à 21 jours" → comparative, 2 breeds
3. "Quel est le poids du Ross 308?" → standard, 1 breed
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.query_router import create_query_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_multi_breed_comparison():
    """Test multi-breed comparison detection"""

    print("\n" + "=" * 80)
    print("TESTS MULTI-BREED COMPARISON")
    print("=" * 80)

    # Create router
    router = create_query_router("config")

    # Test cases: (query, language, expected_destination, expected_breeds_count)
    test_cases = [
        # CAS 1: Comparison explicite avec "vs"
        (
            "Compare le poids de Ross 308 vs Cobb 500 à 35 jours",
            "fr",
            "comparative",
            2,
            ["Ross 308", "Cobb 500"]
        ),

        # CAS 2: Comparison avec "et"
        (
            "Ross 308 et Cobb 500 à 21 jours",
            "fr",
            "comparative",
            2,
            ["Ross 308", "Cobb 500"]
        ),

        # CAS 3: Query standard (pas de comparaison)
        (
            "Quel est le poids du Ross 308 à 35 jours ?",
            "fr",
            "postgresql",
            1,
            ["Ross 308"]
        ),

        # CAS 4: Comparison EN
        (
            "Compare Ross 308 versus Cobb 500 at 35 days",
            "en",
            "comparative",
            2,
            ["Ross 308", "Cobb 500"]
        ),

        # CAS 5: Comparison avec 3 breeds
        (
            "Comparer Ross 308 vs Cobb 500 vs Hubbard à 28 jours",
            "fr",
            "comparative",
            3,
            ["Ross 308", "Cobb 500", "Hubbard"]
        ),

        # CAS 6: Query avec breed unique malgré "compare"
        (
            "Comment comparer les performances du Ross 308 ?",
            "fr",
            "postgresql",  # Pas comparative car 1 seule breed
            1,
            ["Ross 308"]
        ),
    ]

    passed = 0
    failed = 0

    for i, (query, language, expected_dest, expected_count, expected_breeds) in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {query[:70]}... ---")
        print(f"Language: {language}")

        try:
            route = router.route(
                query=query,
                user_id=f"test_user_{i}",
                language=language
            )

            destination = route.destination
            entities = route.entities
            comparison_entities = entities.get("comparison_entities", [])
            is_comparative = entities.get("is_comparative", False)

            print(f"Destination: {destination} (expected: {expected_dest})")
            print(f"Is comparative: {is_comparative}")
            print(f"Comparison entities count: {len(comparison_entities)} (expected: {expected_count if expected_dest == 'comparative' else 0})")

            if comparison_entities:
                breeds_found = [ce.get("breed") for ce in comparison_entities]
                print(f"Breeds found: {breeds_found}")
                print(f"Expected breeds: {expected_breeds if expected_dest == 'comparative' else ['N/A']}")

            # Validation
            dest_match = destination == expected_dest

            if expected_dest == "comparative":
                count_match = len(comparison_entities) == expected_count
                breeds_match = all(breed in [ce.get("breed") for ce in comparison_entities] for breed in expected_breeds)
            else:
                count_match = True  # Not applicable for non-comparative
                breeds_match = True

            if dest_match and count_match and breeds_match:
                print("✅ PASS")
                passed += 1
            else:
                print("❌ FAIL - Mismatch detected:")
                if not dest_match:
                    print(f"   - Destination wrong: {destination} != {expected_dest}")
                if not count_match:
                    print(f"   - Breeds count wrong: {len(comparison_entities)} != {expected_count}")
                if not breeds_match:
                    print("   - Breeds mismatch")
                failed += 1

        except Exception as e:
            print(f"❌ FAIL - Exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed}/{len(test_cases)} passed, {failed}/{len(test_cases)} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = test_multi_breed_comparison()
    sys.exit(0 if success else 1)

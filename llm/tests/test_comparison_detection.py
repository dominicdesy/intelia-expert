# -*- coding: utf-8 -*-
"""
test_comparison_detection.py - Tests unitaires pour détection comparative

Tests simples sans dépendances OpenAI
"""

import sys
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_comparison_patterns():
    """Test patterns de comparaison"""

    print("\n" + "=" * 80)
    print("TESTS COMPARISON PATTERNS")
    print("=" * 80)

    # Pattern de comparaison (copié depuis query_router.py)
    comparison_regex = re.compile(
        r"\b(vs\.?|versus|compar[ae]|compare[zr]?|et|and|ou|or)\b",
        re.IGNORECASE
    )

    test_cases = [
        ("Compare Ross 308 vs Cobb 500", True, "vs"),
        ("Ross 308 versus Cobb 500", True, "versus"),
        ("Comparer Ross 308 et Cobb 500", True, "compare"),
        ("Ross 308 et Cobb 500", True, "et"),
        ("Ross 308 and Cobb 500", True, "and"),
        ("Quel est le poids du Ross 308?", False, None),
        ("Performance Ross 308", False, None),
        ("Compare performance", True, "compare"),
    ]

    passed = 0
    failed = 0

    for query, should_match, expected_keyword in test_cases:
        match = comparison_regex.search(query.lower())
        is_match = match is not None

        status = "PASS" if is_match == should_match else "FAIL"
        print(f"[{status}] '{query[:50]}...' -> Match: {is_match} (expected: {should_match})")

        if is_match and expected_keyword:
            keyword_found = match.group()
            print(f"    Keyword: '{keyword_found}' (expected: '{expected_keyword}')")

        if is_match == should_match:
            passed += 1
        else:
            failed += 1

    print(f"\nRESULTS: {passed}/{len(test_cases)} passed, {failed}/{len(test_cases)} failed")
    return failed == 0


def test_breed_extraction():
    """Test extraction de multiples races"""

    print("\n" + "=" * 80)
    print("TESTS BREED EXTRACTION")
    print("=" * 80)

    # Pattern breed simplifié
    breed_aliases = ["ross 308", "cobb 500", "hubbard", "ross", "cobb"]
    breed_aliases_sorted = sorted(breed_aliases, key=len, reverse=True)
    breed_pattern = "|".join(re.escape(alias) for alias in breed_aliases_sorted)
    breed_regex = re.compile(rf"\b({breed_pattern})\b", re.IGNORECASE)

    test_cases = [
        ("Ross 308 vs Cobb 500", ["ross 308", "cobb 500"]),
        ("Comparer Ross 308 et Cobb 500", ["ross 308", "cobb 500"]),
        ("Ross 308 vs Cobb 500 vs Hubbard", ["ross 308", "cobb 500", "hubbard"]),
        ("Quel est le poids du Ross 308?", ["ross 308"]),
        ("Ross et Cobb", ["ross", "cobb"]),
    ]

    passed = 0
    failed = 0

    for query, expected_breeds in test_cases:
        breeds_found = []
        for match in breed_regex.finditer(query.lower()):
            breed_text = match.group(1)
            if breed_text not in breeds_found:
                breeds_found.append(breed_text)

        breeds_match = set(breeds_found) == set(expected_breeds)
        status = "PASS" if breeds_match else "FAIL"

        print(f"[{status}] '{query[:50]}...'")
        print(f"    Found: {breeds_found}")
        print(f"    Expected: {expected_breeds}")

        if breeds_match:
            passed += 1
        else:
            failed += 1

    print(f"\nRESULTS: {passed}/{len(test_cases)} passed, {failed}/{len(test_cases)} failed")
    return failed == 0


if __name__ == "__main__":
    success1 = test_comparison_patterns()
    success2 = test_breed_extraction()
    sys.exit(0 if (success1 and success2) else 1)

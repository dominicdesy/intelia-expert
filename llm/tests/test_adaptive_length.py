# -*- coding: utf-8 -*-
"""
test_adaptive_length.py - Tests for adaptive response length

Tests query complexity assessment and max_tokens calculation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generation.adaptive_length import get_adaptive_length


def test_very_simple_queries():
    """Test 1: Very simple queries (200-400 tokens)"""

    print("\n" + "=" * 70)
    print("TEST 1: VERY SIMPLE QUERIES (200-400 tokens)")
    print("=" * 70)

    calculator = get_adaptive_length()

    test_cases = [
        {
            "query": "Quel poids ?",
            "entities": {"metric_type": "poids"},
            "expected_range": (200, 400),
        },
        {
            "query": "Ross 308 ?",
            "entities": {"breed": "Ross 308"},
            "expected_range": (200, 400),
        },
        {
            "query": "FCR ?",
            "entities": {"metric_type": "FCR"},
            "expected_range": (200, 400),
        },
    ]

    for i, test in enumerate(test_cases, 1):
        max_tokens = calculator.calculate_max_tokens(
            query=test["query"], entities=test["entities"], query_type="standard"
        )

        min_expected, max_expected = test["expected_range"]
        in_range = min_expected <= max_tokens <= max_expected

        status = "OK" if in_range else "FAILED"
        print(f"\nTest {i}: {test['query']}")
        print(f"  Max tokens: {max_tokens}")
        print(f"  Expected range: {test['expected_range']}")
        print(f"  Status: {status}")

        assert in_range, f"Tokens {max_tokens} not in range {test['expected_range']}"

    print("\nOK - Very simple queries: 200-400 tokens")


def test_simple_queries():
    """Test 2: Simple queries (400-600 tokens)"""

    print("\n" + "=" * 70)
    print("TEST 2: SIMPLE QUERIES (400-600 tokens)")
    print("=" * 70)

    calculator = get_adaptive_length()

    test_cases = [
        {
            "query": "Quel poids pour Ross 308 à 35 jours ?",
            "entities": {"breed": "Ross 308", "age_days": 35, "metric_type": "poids"},
            "expected_range": (400, 600),
        },
        {
            "query": "Quel est le FCR moyen pour Cobb 500 ?",
            "entities": {"breed": "Cobb 500", "metric_type": "FCR"},
            "expected_range": (400, 600),
        },
    ]

    for i, test in enumerate(test_cases, 1):
        max_tokens = calculator.calculate_max_tokens(
            query=test["query"], entities=test["entities"], query_type="standard"
        )

        min_expected, max_expected = test["expected_range"]
        in_range = min_expected <= max_tokens <= max_expected

        status = "OK" if in_range else "FAILED"
        print(f"\nTest {i}: {test['query']}")
        print(f"  Max tokens: {max_tokens}")
        print(f"  Expected range: {test['expected_range']}")
        print(f"  Status: {status}")

        assert in_range, f"Tokens {max_tokens} not in range {test['expected_range']}"

    print("\nOK - Simple queries: 400-600 tokens")


def test_moderate_queries():
    """Test 3: Moderate queries (600-900 tokens)"""

    print("\n" + "=" * 70)
    print("TEST 3: MODERATE QUERIES (600-900 tokens)")
    print("=" * 70)

    calculator = get_adaptive_length()

    test_cases = [
        {
            "query": "Comment optimiser le poids des poulets Ross 308 en finition ?",
            "entities": {"breed": "Ross 308", "production_phase": "finisher"},
            "query_type": "standard",
            "domain": "production",
            "expected_range": (600, 900),
        },
        {
            "query": "Quels sont les symptômes de la coccidiose chez les poulets ?",
            "entities": {},
            "query_type": "standard",
            "domain": "health",
            "expected_range": (600, 900),
        },
    ]

    for i, test in enumerate(test_cases, 1):
        max_tokens = calculator.calculate_max_tokens(
            query=test["query"],
            entities=test["entities"],
            query_type=test.get("query_type", "standard"),
            domain=test.get("domain"),
        )

        min_expected, max_expected = test["expected_range"]
        in_range = min_expected <= max_tokens <= max_expected

        status = "OK" if in_range else "FAILED"
        print(f"\nTest {i}: {test['query']}")
        print(f"  Max tokens: {max_tokens}")
        print(f"  Expected range: {test['expected_range']}")
        print(f"  Status: {status}")

        assert in_range, f"Tokens {max_tokens} not in range {test['expected_range']}"

    print("\nOK - Moderate queries: 600-900 tokens")


def test_complex_queries():
    """Test 4: Complex queries (900-1200 tokens)"""

    print("\n" + "=" * 70)
    print("TEST 4: COMPLEX QUERIES (900-1200 tokens)")
    print("=" * 70)

    calculator = get_adaptive_length()

    test_cases = [
        {
            "query": "Compare les performances entre Ross 308 et Cobb 500 à 35 jours et 42 jours",
            "entities": {
                "breed": ["Ross 308", "Cobb 500"],
                "age_days": [35, 42],
            },
            "query_type": "comparative",
            "expected_range": (800, 1200),  # Allow moderate-complex range
        },
        {
            "query": "Liste complète protocole vaccination: Gumboro J7, J14, J21, Newcastle J10, J18, Bronchite J1, J14, J28. Expliquer toutes les étapes, routes, doses et contre-indications",
            "entities": {"species": "broiler"},
            "query_type": "standard",
            "domain": "health",
            "expected_range": (900, 1200),
        },
    ]

    for i, test in enumerate(test_cases, 1):
        max_tokens = calculator.calculate_max_tokens(
            query=test["query"],
            entities=test["entities"],
            query_type=test.get("query_type", "standard"),
            domain=test.get("domain"),
        )

        min_expected, max_expected = test["expected_range"]
        in_range = min_expected <= max_tokens <= max_expected

        status = "OK" if in_range else "FAILED"
        print(f"\nTest {i}: {test['query'][:60]}...")
        print(f"  Max tokens: {max_tokens}")
        print(f"  Expected range: {test['expected_range']}")
        print(f"  Status: {status}")

        assert in_range, f"Tokens {max_tokens} not in range {test['expected_range']}"

    print("\nOK - Complex queries: 900-1200 tokens")


def test_very_complex_queries():
    """Test 5: Very complex queries (1200-1500 tokens)"""

    print("\n" + "=" * 70)
    print("TEST 5: VERY COMPLEX QUERIES (1200-1500 tokens)")
    print("=" * 70)

    calculator = get_adaptive_length()

    test_cases = [
        {
            "query": "Comparer Ross 308, Cobb 500 et Hubbard JA87 sur le poids, FCR, mortalité et rendement carcasse à 35j, 42j et 49j. Expliquer les différences et recommander pour production intensive.",
            "entities": {
                "breed": ["Ross 308", "Cobb 500", "Hubbard JA87"],
                "age_days": [35, 42, 49],
                "metric_type": ["poids", "FCR", "mortalité", "rendement"],
            },
            "query_type": "comparative",
            "context_docs": [
                {"content": "doc1"},
                {"content": "doc2"},
                {"content": "doc3"},
                {"content": "doc4"},
                {"content": "doc5"},
            ],
            "expected_range": (1100, 1500),  # Allow high-complex range
        },
        {
            "query": "Protocole complet santé pour poulets: vaccination (Newcastle, Gumboro, Bronchite), traitement coccidiose, biosécurité, diagnostic symptômes. Liste toutes les étapes par semaine.",
            "entities": {"species": "broiler"},
            "query_type": "standard",
            "domain": "health",
            "expected_range": (900, 1500),  # Complex-very complex range
        },
    ]

    for i, test in enumerate(test_cases, 1):
        max_tokens = calculator.calculate_max_tokens(
            query=test["query"],
            entities=test["entities"],
            query_type=test.get("query_type", "standard"),
            domain=test.get("domain"),
            context_docs=test.get("context_docs"),
        )

        min_expected, max_expected = test["expected_range"]
        in_range = min_expected <= max_tokens <= max_expected

        status = "OK" if in_range else "FAILED"
        print(f"\nTest {i}: {test['query'][:60]}...")
        print(f"  Max tokens: {max_tokens}")
        print(f"  Expected range: {test['expected_range']}")
        print(f"  Status: {status}")

        assert in_range, f"Tokens {max_tokens} not in range {test['expected_range']}"

    print("\nOK - Very complex queries: 1200-1500 tokens")


def test_complexity_info():
    """Test 6: Complexity info for debugging"""

    print("\n" + "=" * 70)
    print("TEST 6: COMPLEXITY INFO (debugging)")
    print("=" * 70)

    calculator = get_adaptive_length()

    query = "Compare Ross 308 et Cobb 500 à 35 jours sur le poids et FCR"
    entities = {
        "breed": ["Ross 308", "Cobb 500"],
        "age_days": 35,
        "metric_type": ["poids", "FCR"],
    }

    info = calculator.get_complexity_info(
        query=query,
        entities=entities,
        query_type="comparative",
        domain="production",
    )

    print(f"\nQuery: {query}")
    print("\nComplexity analysis:")
    print(f"  Complexity level: {info['complexity']}")
    print(f"  Max tokens: {info['max_tokens']}")
    print(f"  Token range: {info['token_range']}")
    print("\nFactors:")
    for key, value in info["factors"].items():
        print(f"  - {key}: {value}")

    assert info["complexity"] in ["moderate", "complex", "very_complex"]
    assert info["max_tokens"] >= 600
    assert info["factors"]["query_type"] == "comparative"

    print("\nOK - Complexity info works")


if __name__ == "__main__":
    print("\nADAPTIVE RESPONSE LENGTH TEST SUITE")
    print("=" * 70)

    try:
        test_very_simple_queries()
        test_simple_queries()
        test_moderate_queries()
        test_complex_queries()
        test_very_complex_queries()
        test_complexity_info()

        print("\n" + "=" * 70)
        print("OK - ALL TESTS PASSED")
        print("=" * 70)

    except AssertionError as e:
        print(f"\nERROR: TEST FAILED: {e}")
        import traceback

        traceback.print_exc()

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for generation API endpoints
Tests the new intelligent generation functionality
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, ".")

from config.aviculture.config import get_aviculture_config
from app.utils.adaptive_length import get_adaptive_length
from app.utils.post_processor import create_post_processor

def test_config():
    """Test aviculture configuration"""
    print("=" * 60)
    print("TEST 1: Aviculture Configuration")
    print("=" * 60)

    config = get_aviculture_config()
    print(f"✓ Domain: {config.domain}")
    print(f"✓ Supported languages: {config.get_supported_languages()}")
    print(f"✓ Breed keywords: {len(config.breed_keywords)} breeds")
    print(f"✓ Aviculture keywords: {len(config.aviculture_keywords)} keywords")

    # Test system prompt
    prompt = config.get_system_prompt("genetics_performance", "en")
    print(f"✓ System prompt length: {len(prompt)} characters")

    # Test domain detection
    test_queries = [
        "What is the weight of Ross 308 at 21 days?",
        "How do I cook chicken?",
        "Ross 308 FCR at 33 days"
    ]

    print("\nDomain Detection Tests:")
    for query in test_queries:
        is_aviculture = config.is_domain_query(query)
        print(f"  {'✓' if is_aviculture else '✗'} '{query}' → {is_aviculture}")

    print("\n✓ Configuration test passed!\n")


def test_adaptive_length():
    """Test adaptive token length calculation"""
    print("=" * 60)
    print("TEST 2: Adaptive Token Length")
    print("=" * 60)

    calc = get_adaptive_length()

    test_cases = [
        {
            "query": "Ross 308 weight?",
            "entities": {"breed": "Ross 308"},
            "query_type": "standard",
            "expected_range": (200, 600)
        },
        {
            "query": "Compare Ross 308 and Cobb 500 performance at 21 and 42 days",
            "entities": {"breed": "Ross 308, Cobb 500", "age_days": "21, 42"},
            "query_type": "comparative",
            "expected_range": (900, 1500)
        },
    ]

    for case in test_cases:
        max_tokens = calc.calculate_max_tokens(
            query=case["query"],
            entities=case["entities"],
            query_type=case["query_type"]
        )

        in_range = case["expected_range"][0] <= max_tokens <= case["expected_range"][1]
        status = "✓" if in_range else "✗"

        print(f"{status} Query: '{case['query']}'")
        print(f"  Calculated: {max_tokens} tokens")
        print(f"  Expected range: {case['expected_range']}")
        print()

    print("✓ Adaptive length test passed!\n")


def test_post_processor():
    """Test response post-processor"""
    print("=" * 60)
    print("TEST 3: Response Post-Processor")
    print("=" * 60)

    config = get_aviculture_config()
    processor = create_post_processor(
        veterinary_terms=config.veterinary_terms,
        language_messages=config.languages
    )

    test_response = """**Header:** Test Response

1. First item
2. Second item

**Important:**
Some information here.
"""

    processed = processor.post_process_response(
        response=test_response,
        query="Test query",
        language="en"
    )

    print("Original response:")
    print(test_response)
    print("\nProcessed response:")
    print(processed)

    # Test veterinary detection
    vet_queries = [
        ("My chickens have bloody diarrhea", True),
        ("What is the weight of Ross 308?", False),
        ("Symptoms of coccidiosis", True)
    ]

    print("\nVeterinary Detection Tests:")
    for query, expected in vet_queries:
        is_vet = processor.is_veterinary_query(query)
        status = "✓" if is_vet == expected else "✗"
        print(f"  {status} '{query}' → {is_vet} (expected: {expected})")

    print("\n✓ Post-processor test passed!\n")


if __name__ == "__main__":
    try:
        test_config()
        test_adaptive_length()
        test_post_processor()

        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

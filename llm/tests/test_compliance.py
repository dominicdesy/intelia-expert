#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for compliance wrapper
Tests role-based disclaimers
"""

import sys

sys.path.insert(0, "./app")

from app.utils.compliance import get_compliance_wrapper


def test_compliance_wrapper():
    """Test compliance wrapper with different scenarios"""

    wrapper = get_compliance_wrapper()

    # Test cases
    test_cases = [
        {
            "name": "Veterinarian - General query",
            "query": "What is the ideal temperature for broilers?",
            "user_category": "health_veterinary",
            "is_veterinary": False,
            "language": "en",
            "response": "The ideal temperature for broilers is 18-24°C.",
        },
        {
            "name": "Veterinarian - Health query",
            "query": "How to treat Newcastle disease?",
            "user_category": "health_veterinary",
            "is_veterinary": True,
            "language": "en",
            "response": "Newcastle disease treatment includes isolation and supportive care.",
        },
        {
            "name": "Veterinarian - Biosecurity query",
            "query": "What biosecurity measures for quarantine?",
            "user_category": "health_veterinary",
            "is_veterinary": False,
            "language": "en",
            "response": "Implement 14-day quarantine with strict biosecurity protocols.",
        },
        {
            "name": "Producer - General query",
            "query": "What is FCR?",
            "user_category": "farm_operations",
            "is_veterinary": False,
            "language": "en",
            "response": "FCR (Feed Conversion Ratio) measures feed efficiency.",
        },
        {
            "name": "Producer - Health query",
            "query": "My chickens have diarrhea, what should I do?",
            "user_category": "farm_operations",
            "is_veterinary": True,
            "language": "en",
            "response": "Diarrhea can indicate various health issues. Check water quality and feed.",
        },
        {
            "name": "Producer - Biosecurity query (French)",
            "query": "Que faire en cas d'épidémie dans mon élevage?",
            "user_category": "farm_operations",
            "is_veterinary": True,
            "language": "fr",
            "response": "En cas d'épidémie, isolez immédiatement les animaux affectés.",
        },
        {
            "name": "Management - Strategic query",
            "query": "Should we invest in automated feeders?",
            "user_category": "management_oversight",
            "is_veterinary": False,
            "language": "en",
            "response": "Automated feeders improve efficiency by 15-20% and reduce labor costs.",
        },
        {
            "name": "Unknown user - Health query",
            "query": "How to prevent coccidiosis?",
            "user_category": None,
            "is_veterinary": True,
            "language": "en",
            "response": "Prevent coccidiosis through proper sanitation and vaccination programs.",
        },
    ]

    print("\n" + "=" * 80)
    print("COMPLIANCE WRAPPER TEST RESULTS")
    print("=" * 80 + "\n")

    for i, test in enumerate(test_cases, 1):
        print(f"\n[TEST {i}] {test['name']}")
        print("-" * 80)
        print(f"Query: {test['query']}")
        print(f"User: {test['user_category'] or 'unknown'}")
        print(f"Veterinary: {test['is_veterinary']}")
        print(f"Language: {test['language']}")
        print()

        wrapped, metadata = wrapper.wrap_response(
            response=test["response"],
            query=test["query"],
            user_category=test["user_category"],
            is_veterinary_query=test["is_veterinary"],
            language=test["language"],
        )

        print(f"Compliance Level: {metadata['compliance_level']}")
        print(f"Disclaimer Added: {metadata['disclaimer_added']}")
        if metadata["disclaimer_added"]:
            print(f"Disclaimer Length: {metadata['disclaimer_length']} chars")
        print()
        print("RESPONSE:")
        print(wrapped)
        print()

    print("=" * 80)
    print("[OK] All compliance tests completed")
    print("=" * 80)


if __name__ == "__main__":
    test_compliance_wrapper()

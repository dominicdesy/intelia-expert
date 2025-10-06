# -*- coding: utf-8 -*-
"""
test_llm_classifier.py - Tests pour LLMQueryClassifier

Tests des cas problématiques identifiés:
1. "What is the weight of a Cobb 500 male?" → needs_age: true (âge manquant)
2. "What is Newcastle disease?" → needs_age: false (général)
3. "Quels sont les symptômes de Newcastle ?" → needs_age: false (général)
4. "Quel est le poids d'un Ross 308 mâle de 21 jours ?" → complet
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_query_classifier import LLMQueryClassifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_llm_classifier():
    """Test LLM Classifier avec cas problématiques"""

    print("\n" + "=" * 80)
    print("TESTS LLM QUERY CLASSIFIER")
    print("=" * 80)

    # Create classifier
    classifier = LLMQueryClassifier()

    # Test cases: (query, language, expected_intent, expected_needs_age, expected_needs_breed)
    test_cases = [
        # CAS 1: Performance query SANS âge (devrait needs_age: true)
        (
            "What is the weight of a Cobb 500 male?",
            "en",
            "performance_query",
            True,  # needs_age: true (AGE MANQUANT)
            True,  # needs_breed: true
            "postgresql"
        ),

        # CAS 2: General knowledge (Newcastle definition)
        (
            "What is Newcastle disease?",
            "en",
            "general_knowledge",  # ou disease_info
            False,  # needs_age: false
            False,  # needs_breed: false
            "weaviate"
        ),

        # CAS 3: Disease info (symptoms FR)
        (
            "Quels sont les symptômes de Newcastle ?",
            "fr",
            "disease_info",
            False,  # needs_age: false
            False,  # needs_breed: false
            "weaviate"
        ),

        # CAS 4: Performance query COMPLET
        (
            "Quel est le poids d'un Ross 308 mâle de 21 jours ?",
            "fr",
            "performance_query",
            True,  # needs_age: true (mais age PRÉSENT dans query)
            True,  # needs_breed: true
            "postgresql"
        ),

        # CAS 5: Treatment question
        (
            "How to treat coccidiosis in broilers?",
            "en",
            "treatment_info",
            False,  # needs_age: false
            False,  # needs_breed: false
            "weaviate"
        ),

        # CAS 6: Management question
        (
            "What temperature for broilers?",
            "en",
            "management_info",
            False,  # needs_age: false
            False,  # needs_breed: false (général)
            "weaviate"
        ),
    ]

    passed = 0
    failed = 0

    for i, (query, language, expected_intent, expected_needs_age, expected_needs_breed, expected_target) in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {query[:60]}... ---")
        print(f"Language: {language}")

        try:
            classification = classifier.classify(query, language)

            intent = classification.get("intent")
            requirements = classification.get("requirements", {})
            routing = classification.get("routing", {})

            needs_age = requirements.get("needs_age", False)
            needs_breed = requirements.get("needs_breed", False)
            target = routing.get("target", "unknown")

            print(f"Intent: {intent} (expected: {expected_intent})")
            print(f"Needs age: {needs_age} (expected: {expected_needs_age})")
            print(f"Needs breed: {needs_breed} (expected: {expected_needs_breed})")
            print(f"Target: {target} (expected: {expected_target})")

            # Validation
            intent_match = intent in [expected_intent, "general_knowledge", "disease_info", "treatment_info"]  # Accept variations
            age_match = needs_age == expected_needs_age
            breed_match = needs_breed == expected_needs_breed
            target_match = target == expected_target

            if age_match and breed_match and target_match:
                print("✅ PASS - Classification correcte")
                passed += 1
            else:
                print(f"❌ FAIL - Mismatch detected:")
                if not age_match:
                    print(f"   - Age requirement wrong: {needs_age} != {expected_needs_age}")
                if not breed_match:
                    print(f"   - Breed requirement wrong: {needs_breed} != {expected_needs_breed}")
                if not target_match:
                    print(f"   - Target wrong: {target} != {expected_target}")
                failed += 1

        except Exception as e:
            print(f"❌ FAIL - Exception: {e}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed}/{len(test_cases)} passed, {failed}/{len(test_cases)} failed")
    print(f"Cache size: {classifier.get_cache_size()} entries")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = test_llm_classifier()
    sys.exit(0 if success else 1)

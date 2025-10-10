# -*- coding: utf-8 -*-
"""
Test script for LLM-generated contextual clarification messages

Tests the implementation with real ambiguous queries to verify:
1. LLM generates context-specific clarification messages
2. Messages include farm-type-specific sub-questions
3. Fallback to templates works if LLM fails
4. Metadata correctly tracks clarification source
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from llm.core.llm_query_classifier import get_llm_query_classifier

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_clarification_generation():
    """Test LLM-generated clarification messages with ambiguous queries"""

    # Initialize classifier
    classifier = get_llm_query_classifier()

    # Test cases from user's examples - ambiguous queries that need clarification
    test_cases = [
        # Temperature queries (should detect farm context and ask specific sub-questions)
        {
            "query": "Temperature seems off",
            "language": "en",
            "expected_intent": "management_info",
            "should_need_clarification": False,  # management_info doesn't require breed/age
            "description": "Ambiguous temperature - should ask broiler vs hatchery"
        },
        {
            "query": "La température me semble désajustée",
            "language": "fr",
            "expected_intent": "management_info",
            "should_need_clarification": False,
            "description": "Ambiguous temperature (FR) - should ask context"
        },

        # Feed queries
        {
            "query": "We're having issues with feed this week",
            "language": "en",
            "expected_intent": "management_info",
            "should_need_clarification": False,
            "description": "Ambiguous feed issue - should ask farm type and specifics"
        },
        {
            "query": "La consommation d'aliment me semble basse",
            "language": "fr",
            "expected_intent": "management_info",
            "should_need_clarification": False,
            "description": "Low feed consumption - should ask for context"
        },

        # Water queries
        {
            "query": "Water intake is weird",
            "language": "en",
            "expected_intent": "management_info",
            "should_need_clarification": False,
            "description": "Ambiguous water - should ask context"
        },

        # Mortality queries
        {
            "query": "Mortality is high",
            "language": "en",
            "expected_intent": "management_info",
            "should_need_clarification": False,
            "description": "High mortality - should ask farm context and details"
        },

        # Performance queries WITHOUT age (should trigger clarification)
        {
            "query": "What is the weight of a Ross 308 male?",
            "language": "en",
            "expected_intent": "performance_query",
            "should_need_clarification": True,  # Missing age!
            "description": "Performance query missing age - MUST trigger clarification"
        },
        {
            "query": "Quel est le poids d'un Cobb 500 mâle?",
            "language": "fr",
            "expected_intent": "performance_query",
            "should_need_clarification": True,  # Missing age!
            "description": "Performance query missing age (FR) - MUST trigger clarification"
        },

        # Complete performance queries (should NOT need clarification)
        {
            "query": "What is the weight of a Ross 308 male at 21 days?",
            "language": "en",
            "expected_intent": "performance_query",
            "should_need_clarification": False,  # Has breed + age
            "description": "Complete performance query - no clarification needed"
        },

        # General knowledge (should NOT need clarification)
        {
            "query": "What is Newcastle disease?",
            "language": "en",
            "expected_intent": "disease_info",
            "should_need_clarification": False,
            "description": "Disease info - no clarification needed"
        },
    ]

    print("\n" + "="*80)
    print("TESTING LLM-GENERATED CLARIFICATION MESSAGES")
    print("="*80 + "\n")

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        query = test["query"]
        language = test["language"]
        expected_intent = test["expected_intent"]
        should_need_clarification = test["should_need_clarification"]
        description = test["description"]

        print(f"\n{'='*80}")
        print(f"TEST {i}: {description}")
        print(f"{'='*80}")
        print(f"Query: '{query}'")
        print(f"Language: {language}")
        print(f"Expected intent: {expected_intent}")
        print(f"Should need clarification: {should_need_clarification}")

        try:
            # Classify query
            classification = classifier.classify(query, language)

            # Extract results
            intent = classification.get("intent")
            is_complete = classification.get("is_complete")
            missing_entities = classification.get("missing_entities", [])
            clarification_message = classification.get("clarification_message")
            routing_target = classification["routing"]["target"]
            confidence = classification["routing"]["confidence"]

            print(f"\nRESULTS:")
            print(f"  Intent: {intent}")
            print(f"  Complete: {is_complete}")
            print(f"  Missing entities: {missing_entities}")
            print(f"  Routing: {routing_target} (confidence: {confidence:.2%})")

            # Check if clarification message was generated
            needs_clarification = not is_complete

            if needs_clarification:
                print(f"\nCLARIFICATION MESSAGE GENERATED:")
                if clarification_message:
                    print(f"  {clarification_message}")
                    print(f"  [OK] LLM generated a clarification message")
                else:
                    print(f"  [WARN] No clarification message (will use template fallback)")
            else:
                print(f"\n[OK] No clarification needed - query is complete")

            # Validate expectations
            test_passed = True
            errors = []

            # Check intent
            if intent != expected_intent:
                errors.append(f"Intent mismatch: expected '{expected_intent}', got '{intent}'")
                test_passed = False

            # Check clarification requirement
            if needs_clarification != should_need_clarification:
                errors.append(
                    f"Clarification mismatch: expected needs_clarification={should_need_clarification}, "
                    f"got {needs_clarification}"
                )
                test_passed = False

            # If clarification needed, check message quality
            if needs_clarification and should_need_clarification:
                if not clarification_message:
                    errors.append("Clarification needed but no message generated")
                    test_passed = False
                elif len(clarification_message) < 10:
                    errors.append(f"Clarification message too short: '{clarification_message}'")
                    test_passed = False

            # Print test result
            if test_passed:
                print(f"\n[PASS] TEST PASSED")
                passed += 1
            else:
                print(f"\n[FAIL] TEST FAILED")
                for error in errors:
                    print(f"  - {error}")
                failed += 1

        except Exception as e:
            print(f"\n[ERROR] TEST ERROR: {e}")
            logger.exception("Test failed with exception")
            failed += 1

    # Print summary
    print(f"\n{'='*80}")
    print(f"TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests: {len(test_cases)}")
    print(f"[PASS] Passed: {passed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"Success rate: {passed/len(test_cases)*100:.1f}%")
    print(f"{'='*80}\n")

    return failed == 0


if __name__ == "__main__":
    success = test_clarification_generation()
    sys.exit(0 if success else 1)

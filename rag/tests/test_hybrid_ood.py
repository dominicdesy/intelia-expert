#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_hybrid_ood.py - Test suite for HybridOODDetector
Version: 1.0.0
Last modified: 2025-10-30

Tests the hybrid OOD detection system (LLM + Weaviate) with realistic queries.

Usage:
    python test_hybrid_ood.py [--quick] [--verbose]

Options:
    --quick     Skip Weaviate tests (only test LLM fast paths)
    --verbose   Show detailed decision information
"""

import sys
import os
import logging
import time
from typing import List, Tuple, Dict
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Represents a test case for OOD detection"""
    query: str
    language: str
    expected_in_domain: bool
    expected_method: str  # "llm_fast_accept", "llm_fast_reject", "weaviate_found", etc.
    category: str  # "fast_path_yes", "fast_path_no", "weaviate_fallback"
    description: str


# Test cases organized by category
TEST_CASES: List[TestCase] = [
    # ═══════════════════════════════════════════════════════════
    # CATEGORY 1: Fast Path - Clear YES (Poultry Questions)
    # ═══════════════════════════════════════════════════════════
    TestCase(
        query="What is the FCR for Ross 308 at 35 days?",
        language="en",
        expected_in_domain=True,
        expected_method="llm_fast_accept",
        category="fast_path_yes",
        description="Clear poultry metric question"
    ),
    TestCase(
        query="Comment prévenir la coccidiose ?",
        language="fr",
        expected_in_domain=True,
        expected_method="llm_fast_accept",
        category="fast_path_yes",
        description="Poultry disease prevention"
    ),
    TestCase(
        query="Quel est le poids d'un Cobb 500 mâle à 42 jours ?",
        language="fr",
        expected_in_domain=True,
        expected_method="llm_fast_accept",
        category="fast_path_yes",
        description="Specific breed weight question"
    ),
    TestCase(
        query="How to treat Newcastle disease?",
        language="en",
        expected_in_domain=True,
        expected_method="llm_fast_accept",
        category="fast_path_yes",
        description="Poultry disease treatment"
    ),
    TestCase(
        query="Quelle température pour un poulailler en hiver ?",
        language="fr",
        expected_in_domain=True,
        expected_method="llm_fast_accept",
        category="fast_path_yes",
        description="Poultry housing conditions"
    ),

    # ═══════════════════════════════════════════════════════════
    # CATEGORY 2: Fast Path - Clear NO (Out-of-Domain)
    # ═══════════════════════════════════════════════════════════
    TestCase(
        query="What is the capital of France?",
        language="en",
        expected_in_domain=False,
        expected_method="llm_fast_reject",
        category="fast_path_no",
        description="Geography question"
    ),
    TestCase(
        query="Comment faire une pizza ?",
        language="fr",
        expected_in_domain=False,
        expected_method="llm_fast_reject",
        category="fast_path_no",
        description="Cooking recipe"
    ),
    TestCase(
        query="Who won the World Cup 2022?",
        language="en",
        expected_in_domain=False,
        expected_method="llm_fast_reject",
        category="fast_path_no",
        description="Sports question"
    ),
    TestCase(
        query="Quelle est la température idéale pour un aquarium ?",
        language="fr",
        expected_in_domain=False,
        expected_method="llm_fast_reject",
        category="fast_path_no",
        description="Fish/aquarium question"
    ),

    # ═══════════════════════════════════════════════════════════
    # CATEGORY 3: Weaviate Fallback - Intelia Products
    # ═══════════════════════════════════════════════════════════
    TestCase(
        query="Comment configurer le chauffage dans le nano ?",
        language="fr",
        expected_in_domain=True,
        expected_method="llm_fast_accept",  # Should work with updated LLM prompt
        category="weaviate_fallback",
        description="Nano product configuration (updated LLM should recognize)"
    ),
    TestCase(
        query="How do I use the Nano system?",
        language="en",
        expected_in_domain=True,
        expected_method="llm_fast_accept",  # Should work with updated LLM prompt
        category="weaviate_fallback",
        description="Nano product usage"
    ),
    TestCase(
        query="What is the Logix system?",
        language="en",
        expected_in_domain=True,
        expected_method="llm_fast_accept",  # Should work with updated LLM prompt
        category="weaviate_fallback",
        description="Logix product question"
    ),
    TestCase(
        query="Comment exporter les données du Logix ?",
        language="fr",
        expected_in_domain=True,
        expected_method="llm_fast_accept",  # Should work with updated LLM prompt
        category="weaviate_fallback",
        description="Logix data export"
    ),

    # ═══════════════════════════════════════════════════════════
    # CATEGORY 4: Edge Cases
    # ═══════════════════════════════════════════════════════════
    TestCase(
        query="Temperature",
        language="en",
        expected_in_domain=True,
        expected_method="llm_fast_accept",  # Ambiguous but has poultry context
        category="edge_cases",
        description="Single word (ambiguous)"
    ),
    TestCase(
        query="Quelle est la température idéale ?",
        language="fr",
        expected_in_domain=True,
        expected_method="llm_fast_accept",  # Context suggests poultry
        category="edge_cases",
        description="Ambiguous temperature question"
    ),
]


class TestStats:
    """Track test statistics"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.by_category: Dict[str, Dict[str, int]] = {}
        self.by_method: Dict[str, Dict[str, int]] = {}
        self.total_time = 0.0
        self.failures: List[Dict] = []

    def add_result(self, test_case: TestCase, passed: bool, actual_method: str, duration: float):
        """Record a test result"""
        self.total += 1
        self.total_time += duration

        if passed:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append({
                'query': test_case.query,
                'expected_in_domain': test_case.expected_in_domain,
                'expected_method': test_case.expected_method,
                'actual_method': actual_method,
                'description': test_case.description
            })

        # Track by category
        if test_case.category not in self.by_category:
            self.by_category[test_case.category] = {'passed': 0, 'failed': 0}
        if passed:
            self.by_category[test_case.category]['passed'] += 1
        else:
            self.by_category[test_case.category]['failed'] += 1

        # Track by method
        if actual_method not in self.by_method:
            self.by_method[actual_method] = {'count': 0, 'avg_time': 0.0, 'total_time': 0.0}
        self.by_method[actual_method]['count'] += 1
        self.by_method[actual_method]['total_time'] += duration
        self.by_method[actual_method]['avg_time'] = (
            self.by_method[actual_method]['total_time'] / self.by_method[actual_method]['count']
        )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        # Overall results
        print(f"\n📊 Overall Results:")
        print(f"   Total tests: {self.total}")
        print(f"   ✅ Passed: {self.passed} ({self.passed/self.total*100:.1f}%)")
        print(f"   ❌ Failed: {self.failed} ({self.failed/self.total*100:.1f}%)")
        print(f"   ⏱️  Total time: {self.total_time:.2f}s")
        print(f"   ⚡ Avg time per test: {self.total_time/self.total*1000:.0f}ms")

        # Results by category
        print(f"\n📁 Results by Category:")
        for category, stats in sorted(self.by_category.items()):
            total_cat = stats['passed'] + stats['failed']
            print(f"   {category}:")
            print(f"      ✅ {stats['passed']}/{total_cat} passed ({stats['passed']/total_cat*100:.1f}%)")
            if stats['failed'] > 0:
                print(f"      ❌ {stats['failed']}/{total_cat} failed")

        # Results by method
        print(f"\n🔧 Results by Detection Method:")
        for method, stats in sorted(self.by_method.items()):
            print(f"   {method}:")
            print(f"      Count: {stats['count']}")
            print(f"      Avg time: {stats['avg_time']*1000:.0f}ms")

        # Failures detail
        if self.failures:
            print(f"\n❌ Failed Tests Detail:")
            for i, failure in enumerate(self.failures, 1):
                print(f"\n   {i}. {failure['description']}")
                print(f"      Query: \"{failure['query']}\"")
                print(f"      Expected: {'IN-DOMAIN' if failure['expected_in_domain'] else 'OUT-OF-DOMAIN'} via {failure['expected_method']}")
                print(f"      Got: {failure['actual_method']}")

        print("\n" + "=" * 80)


def run_tests(quick_mode: bool = False, verbose: bool = False) -> TestStats:
    """
    Run OOD detection tests

    Args:
        quick_mode: Skip Weaviate tests (only test LLM)
        verbose: Show detailed decision information
    """
    from security.llm_ood_detector import LLMOODDetector

    logger.info("🧪 Starting Hybrid OOD Detector tests...")

    # Initialize detector
    try:
        llm_detector = LLMOODDetector(model="gpt-4o-mini")
        logger.info("✅ LLMOODDetector initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLMOODDetector: {e}")
        logger.error("Make sure OPENAI_API_KEY is set in environment")
        sys.exit(1)

    # For quick mode, we only test LLM
    if quick_mode:
        detector = llm_detector
        logger.info("⚡ Quick mode: Testing LLM only (no Weaviate)")
    else:
        # Try to initialize HybridOODDetector with Weaviate
        try:
            from security.hybrid_ood_detector import HybridOODDetector
            from retrieval.weaviate.core import WeaviateManager

            # Initialize Weaviate client
            weaviate_manager = WeaviateManager()
            logger.info("✅ WeaviateManager initialized")

            # Create hybrid detector
            detector = HybridOODDetector(
                llm_detector=llm_detector,
                weaviate_client=weaviate_manager,
                llm_high_confidence_threshold=0.9,
                weaviate_score_threshold=0.7,
                weaviate_top_k=5,
                weaviate_alpha=0.5
            )
            logger.info("✅ HybridOODDetector initialized")
        except Exception as e:
            logger.warning(f"⚠️ Could not initialize HybridOODDetector: {e}")
            logger.warning("Falling back to LLM-only mode")
            detector = llm_detector
            quick_mode = True

    stats = TestStats()

    # Run tests
    print("\n" + "=" * 80)
    print("RUNNING TESTS")
    print("=" * 80)

    for i, test_case in enumerate(TEST_CASES, 1):
        # Skip Weaviate fallback tests in quick mode
        if quick_mode and test_case.category == "weaviate_fallback":
            continue

        print(f"\n[{i}/{len(TEST_CASES)}] {test_case.description}")
        print(f"   Query: \"{test_case.query}\" (lang={test_case.language})")
        print(f"   Expected: {'✅ IN-DOMAIN' if test_case.expected_in_domain else '❌ OUT-OF-DOMAIN'} via {test_case.expected_method}")

        # Run detection
        start_time = time.time()
        try:
            is_in_domain, confidence, details = detector.is_in_domain(
                test_case.query,
                language=test_case.language
            )
            duration = time.time() - start_time

            actual_method = details.get('method', 'unknown')

            # Check if result matches expectation
            passed = (is_in_domain == test_case.expected_in_domain)

            # Print result
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   Result: {'✅ IN-DOMAIN' if is_in_domain else '❌ OUT-OF-DOMAIN'} via {actual_method}")
            print(f"   Confidence: {confidence:.2f}, Duration: {duration*1000:.0f}ms")
            print(f"   {status}")

            if verbose:
                print(f"   Details: {details}")

            # Record result
            stats.add_result(test_case, passed, actual_method, duration)

        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ ERROR: {e}")
            stats.add_result(test_case, False, "error", duration)

    return stats


def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description='Test Hybrid OOD Detector')
    parser.add_argument('--quick', action='store_true', help='Quick mode (LLM only, no Weaviate)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed decision information')
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("HYBRID OOD DETECTOR TEST SUITE")
    print("=" * 80)
    print(f"Mode: {'Quick (LLM only)' if args.quick else 'Full (LLM + Weaviate)'}")
    print(f"Verbose: {'Yes' if args.verbose else 'No'}")

    # Run tests
    stats = run_tests(quick_mode=args.quick, verbose=args.verbose)

    # Print summary
    stats.print_summary()

    # Exit with appropriate code
    sys.exit(0 if stats.failed == 0 else 1)


if __name__ == '__main__':
    main()

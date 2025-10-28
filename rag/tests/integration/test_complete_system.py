# -*- coding: utf-8 -*-
"""
test_complete_system.py - Complete Integration Test Suite

Executes 100 realistic queries through the entire RAG pipeline:
- Entity Extraction (89 entity types)
- Multi-Retriever System (PostgreSQL + ChromaDB)
- Multi-LLM Router (OpenAI, Anthropic, DeepSeek)
- Response Generation with Proactive Assistant

Validates:
- Response quality and length
- Entity extraction accuracy
- Proactive follow-up generation
- Performance metrics (latency, cost)

Usage:
    python test_complete_system.py
    python test_complete_system.py --verbose
    python test_complete_system.py --queries 10  # Run first 10 only
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import system components
from core.intent_classifier import IntentClassifier
from retrieval.retriever import create_retriever
from generation.response_generator import ResponseGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test query"""

    query_id: int
    query: str
    language: str
    domain: str
    success: bool
    response: str = ""
    entities_extracted: Dict[str, Any] = field(default_factory=dict)
    follow_up_generated: bool = False
    latency_ms: float = 0.0
    retrieval_docs_count: int = 0
    llm_provider: str = ""
    error_message: str = ""

    # Validation results
    length_valid: bool = True
    entities_valid: bool = True
    response_quality_valid: bool = True


@dataclass
class TestSummary:
    """Summary of all test results"""

    total_queries: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0.0

    # Performance metrics
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    total_time_seconds: float = 0.0

    # Entity extraction
    entity_extraction_success_rate: float = 0.0
    total_entities_extracted: int = 0

    # Proactive assistant
    follow_up_generation_rate: float = 0.0

    # LLM routing
    llm_usage: Dict[str, int] = field(default_factory=dict)

    # Quality metrics
    avg_response_length: float = 0.0
    length_validation_rate: float = 0.0

    # Cost estimation (approximate)
    estimated_total_cost_usd: float = 0.0

    # Failures
    failures: List[Dict[str, Any]] = field(default_factory=list)


class CompleteSystemTester:
    """
    Complete integration test runner

    Executes queries through the entire RAG pipeline and validates results
    """

    def __init__(
        self,
        queries_file: str = "test_queries.json",
        verbose: bool = False,
        max_queries: Optional[int] = None,
    ):
        """
        Initialize test runner

        Args:
            queries_file: Path to test queries JSON file
            verbose: Enable verbose logging
            max_queries: Limit number of queries to run (for quick tests)
        """
        self.queries_file = Path(__file__).parent / queries_file
        self.verbose = verbose
        self.max_queries = max_queries

        # Results storage
        self.results: List[TestResult] = []
        self.summary: TestSummary = TestSummary()

        # System components (initialized in setup)
        self.intent_classifier = None
        self.retriever = None
        self.generator = None

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    async def setup(self):
        """Initialize all system components"""
        logger.info("Initializing system components...")

        try:
            # Initialize Intent Classifier
            from openai import AsyncOpenAI
            import os

            openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.intent_classifier = IntentClassifier(client=openai_client)
            logger.info("OK - Intent Classifier initialized")

            # Initialize Retriever (PostgreSQL + ChromaDB)
            self.retriever = await create_retriever()
            logger.info("OK - Multi-Retriever initialized")

            # Initialize Response Generator
            self.generator = ResponseGenerator(
                client=openai_client,
                cache_manager=None,  # Disable cache for testing
                language="fr",
            )
            logger.info("OK - Response Generator initialized")

            logger.info("OK - All components initialized successfully")

        except Exception as e:
            logger.error(f"FAIL - Failed to initialize components: {e}")
            raise

    def load_queries(self) -> List[Dict[str, Any]]:
        """Load test queries from JSON file"""
        logger.info(f"Loading test queries from {self.queries_file}...")

        with open(self.queries_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        queries = data["queries"]

        if self.max_queries:
            queries = queries[: self.max_queries]
            logger.info(f"Limited to first {self.max_queries} queries")

        logger.info(f"Loaded {len(queries)} test queries")
        return queries

    async def run_single_query(self, test_query: Dict[str, Any]) -> TestResult:
        """
        Execute a single test query through the complete pipeline

        Args:
            test_query: Test query specification

        Returns:
            TestResult with validation and metrics
        """
        query_id = test_query["id"]
        query = test_query["query"]
        language = test_query["language"]
        domain = test_query["domain"]

        if self.verbose:
            logger.info(f"\n{'='*70}")
            logger.info(f"TEST {query_id}: {query}")
            logger.info(f"Language: {language}, Domain: {domain}")
            logger.info(f"{'='*70}")

        result = TestResult(
            query_id=query_id,
            query=query,
            language=language,
            domain=domain,
            success=False,
        )

        start_time = time.time()

        try:
            # Step 1: Intent Classification & Entity Extraction
            intent_result = await self.intent_classifier.classify_intent(
                query, language
            )
            result.entities_extracted = intent_result.get("entities", {})

            if self.verbose:
                logger.info(f"Entities extracted: {result.entities_extracted}")

            # Step 2: Retrieval
            context_docs = await self.retriever.retrieve(query, intent_result, top_k=5)
            result.retrieval_docs_count = len(context_docs)

            if self.verbose:
                logger.info(f"Retrieved {result.retrieval_docs_count} documents")

            # Step 3: Response Generation with Proactive Assistant
            response = await self.generator.generate_response(
                query=query,
                context_docs=context_docs,
                language=language,
                intent_result=intent_result,
            )
            result.response = response

            # Check if follow-up was generated (contains "?" in last 200 chars)
            result.follow_up_generated = "?" in response[-200:]

            if self.verbose:
                logger.info(f"Response length: {len(response)} chars")
                logger.info(f"Follow-up generated: {result.follow_up_generated}")
                logger.info(f"Response preview: {response[:200]}...")

            # Calculate latency
            result.latency_ms = (time.time() - start_time) * 1000

            # Validation
            self._validate_result(result, test_query)

            result.success = True

            if self.verbose:
                logger.info(f"OK - Test {query_id} PASSED ({result.latency_ms:.0f}ms)")

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.latency_ms = (time.time() - start_time) * 1000

            logger.error(f"FAIL - Test {query_id} FAILED: {e}")

        return result

    def _validate_result(self, result: TestResult, test_query: Dict[str, Any]):
        """
        Validate test result against expectations

        Args:
            result: TestResult to validate
            test_query: Expected values
        """
        # Validate response length
        min_length = test_query.get("min_response_length", 100)
        max_length = test_query.get("max_response_length", 2000)
        response_length = len(result.response)

        result.length_valid = min_length <= response_length <= max_length

        if not result.length_valid and self.verbose:
            logger.warning(
                f"Length validation failed: {response_length} not in [{min_length}, {max_length}]"
            )

        # Validate entity extraction
        expected_entities = test_query.get("expected_entities", [])
        if expected_entities:
            extracted_keys = set(result.entities_extracted.keys())
            # At least 50% of expected entities should be extracted
            match_rate = len(extracted_keys & set(expected_entities)) / len(
                expected_entities
            )
            result.entities_valid = match_rate >= 0.5

            if not result.entities_valid and self.verbose:
                logger.warning(
                    f"Entity validation failed: only {match_rate*100:.0f}% of expected entities found"
                )

        # Validate response quality
        result.response_quality_valid = (
            result.response
            and len(result.response) > 50
            and result.response
            != "Désolé, je ne peux pas générer une réponse pour cette question."
        )

    async def run_all_tests(self):
        """Execute all test queries and generate summary"""
        logger.info("\n" + "=" * 70)
        logger.info("COMPLETE SYSTEM INTEGRATION TEST SUITE")
        logger.info("=" * 70)

        # Load queries
        queries = self.load_queries()
        self.summary.total_queries = len(queries)

        # Run tests
        logger.info(f"\nExecuting {len(queries)} test queries...")
        start_time = time.time()

        for i, test_query in enumerate(queries, 1):
            if not self.verbose:
                print(
                    f"\rProgress: {i}/{len(queries)} ({i*100//len(queries)}%)", end=""
                )

            result = await self.run_single_query(test_query)
            self.results.append(result)

            # Small delay to avoid rate limits
            await asyncio.sleep(0.1)

        if not self.verbose:
            print()  # New line after progress

        self.summary.total_time_seconds = time.time() - start_time

        # Generate summary
        self._generate_summary()

        # Print report
        self._print_report()

        # Save detailed results
        self._save_results()

    def _generate_summary(self):
        """Generate test summary from results"""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        self.summary.successful = len(successful)
        self.summary.failed = len(failed)
        self.summary.success_rate = (
            len(successful) / len(self.results) * 100 if self.results else 0
        )

        # Performance metrics
        if successful:
            latencies = [r.latency_ms for r in successful]
            self.summary.avg_latency_ms = sum(latencies) / len(latencies)
            self.summary.min_latency_ms = min(latencies)
            self.summary.max_latency_ms = max(latencies)

        # Entity extraction
        total_with_entities = sum(1 for r in successful if r.entities_extracted)
        self.summary.entity_extraction_success_rate = (
            total_with_entities / len(successful) * 100 if successful else 0
        )
        self.summary.total_entities_extracted = sum(
            len(r.entities_extracted) for r in successful
        )

        # Proactive assistant
        total_with_followup = sum(1 for r in successful if r.follow_up_generated)
        self.summary.follow_up_generation_rate = (
            total_with_followup / len(successful) * 100 if successful else 0
        )

        # Quality metrics
        if successful:
            response_lengths = [len(r.response) for r in successful]
            self.summary.avg_response_length = sum(response_lengths) / len(
                response_lengths
            )

            length_valid_count = sum(1 for r in successful if r.length_valid)
            self.summary.length_validation_rate = (
                length_valid_count / len(successful) * 100
            )

        # Failures
        self.summary.failures = [
            {
                "id": r.query_id,
                "query": r.query,
                "error": r.error_message,
                "language": r.language,
                "domain": r.domain,
            }
            for r in failed
        ]

        # Rough cost estimation (based on typical token usage)
        # Assume avg 2000 input tokens + 500 output tokens per query
        avg_cost_per_query = 0.003  # Rough estimate in USD
        self.summary.estimated_total_cost_usd = len(successful) * avg_cost_per_query

    def _print_report(self):
        """Print comprehensive test report"""
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)

        # Overall results
        print("\nOverall Results:")
        print(f"  Total queries:    {self.summary.total_queries}")
        print(f"  Successful:       {self.summary.successful}")
        print(f"  Failed:           {self.summary.failed}")
        print(f"  Success rate:     {self.summary.success_rate:.1f}%")
        print(f"  Total time:       {self.summary.total_time_seconds:.1f}s")

        # Performance
        print("\nPerformance Metrics:")
        print(f"  Avg latency:      {self.summary.avg_latency_ms:.0f}ms")
        print(f"  Min latency:      {self.summary.min_latency_ms:.0f}ms")
        print(f"  Max latency:      {self.summary.max_latency_ms:.0f}ms")

        # Entity extraction
        print("\nEntity Extraction:")
        print(f"  Success rate:     {self.summary.entity_extraction_success_rate:.1f}%")
        print(f"  Total entities:   {self.summary.total_entities_extracted}")

        # Proactive assistant
        print("\nProactive Assistant:")
        print(f"  Follow-up rate:   {self.summary.follow_up_generation_rate:.1f}%")

        # Quality
        print("\nResponse Quality:")
        print(f"  Avg length:       {self.summary.avg_response_length:.0f} chars")
        print(f"  Length valid:     {self.summary.length_validation_rate:.1f}%")

        # Cost
        print("\nEstimated Cost:")
        print(f"  Total:            ${self.summary.estimated_total_cost_usd:.2f} USD")

        # Failures
        if self.summary.failures:
            print(f"\nFailures ({len(self.summary.failures)}):")
            for failure in self.summary.failures[:5]:  # Show first 5
                print(f"  [{failure['id']}] {failure['query'][:50]}...")
                print(f"      Error: {failure['error'][:80]}")

            if len(self.summary.failures) > 5:
                print(f"  ... and {len(self.summary.failures) - 5} more")

        print("\n" + "=" * 70)

        # Final verdict
        if self.summary.success_rate >= 95:
            print("OK - EXCELLENT: All systems operational")
        elif self.summary.success_rate >= 80:
            print("OK - GOOD: Minor issues detected")
        elif self.summary.success_rate >= 60:
            print("WARNING: Significant issues detected")
        else:
            print("FAIL - CRITICAL: Major system issues")

        print("=" * 70)

    def _save_results(self):
        """Save detailed results to JSON file"""
        output_file = (
            Path(__file__).parent
            / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        results_data = {
            "summary": {
                "total_queries": self.summary.total_queries,
                "successful": self.summary.successful,
                "failed": self.summary.failed,
                "success_rate": self.summary.success_rate,
                "avg_latency_ms": self.summary.avg_latency_ms,
                "total_time_seconds": self.summary.total_time_seconds,
                "entity_extraction_success_rate": self.summary.entity_extraction_success_rate,
                "follow_up_generation_rate": self.summary.follow_up_generation_rate,
                "avg_response_length": self.summary.avg_response_length,
                "estimated_total_cost_usd": self.summary.estimated_total_cost_usd,
            },
            "failures": self.summary.failures,
            "detailed_results": [
                {
                    "query_id": r.query_id,
                    "query": r.query,
                    "language": r.language,
                    "domain": r.domain,
                    "success": r.success,
                    "latency_ms": r.latency_ms,
                    "response_length": len(r.response),
                    "entities_extracted": r.entities_extracted,
                    "follow_up_generated": r.follow_up_generated,
                    "length_valid": r.length_valid,
                    "entities_valid": r.entities_valid,
                    "error": r.error_message if not r.success else None,
                }
                for r in self.results
            ],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        logger.info(f"\nDetailed results saved to: {output_file}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Complete System Integration Test Suite"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--queries", "-q", type=int, help="Limit number of queries to run"
    )
    args = parser.parse_args()

    tester = CompleteSystemTester(verbose=args.verbose, max_queries=args.queries)

    await tester.setup()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

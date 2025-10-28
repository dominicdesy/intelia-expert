# -*- coding: utf-8 -*-
"""
Test script for external sources system

Tests:
1. Individual fetchers (Semantic Scholar, PubMed, Europe PMC)
2. ExternalSourceManager parallel search
3. Document deduplication
4. Ranking algorithm
"""

import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm.external_sources import ExternalSourceManager
from llm.external_sources.fetchers import (
    SemanticScholarFetcher,
    PubMedFetcher,
    EuropePMCFetcher,
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_individual_fetcher(fetcher, name: str, query: str):
    """Test individual fetcher"""
    print(f"\n{'='*80}")
    print(f"Testing {name}")
    print(f"{'='*80}")
    print(f"Query: '{query}'")

    try:
        results = await fetcher.search(query, max_results=3, min_year=2015)

        print(f"\nResults: {len(results)} documents found\n")

        for i, doc in enumerate(results, 1):
            print(f"{i}. {doc.title}")
            print(f"   Authors: {', '.join(doc.authors[:3])}")
            print(f"   Year: {doc.year} | Citations: {doc.citation_count}")
            print(f"   Source: {doc.source}")
            print(f"   DOI: {doc.doi or 'N/A'}")
            print(f"   Abstract: {doc.abstract[:150]}...")
            print()

        return True

    except Exception as e:
        print(f"[ERROR] {name} test failed: {e}")
        logger.exception(f"{name} test failed")
        return False


async def test_parallel_search(manager: ExternalSourceManager, query: str):
    """Test parallel search across all sources"""
    print(f"\n{'='*80}")
    print("Testing Parallel Search (All Sources)")
    print(f"{'='*80}")
    print(f"Query: '{query}'")

    try:
        result = await manager.search(
            query=query, language="en", max_results_per_source=5, min_year=2015
        )

        print("\n[RESULTS]")
        print(f"  Found: {result.found}")
        print(f"  Sources searched: {result.sources_searched}")
        print(f"  Sources succeeded: {result.sources_succeeded}")
        print(f"  Total results: {result.total_results}")
        print(f"  Unique results: {result.unique_results}")
        print(f"  Search duration: {result.search_duration_ms:.0f}ms")

        if result.has_answer():
            print("\n[BEST DOCUMENT]")
            best = result.best_document
            print(f"  Title: {best.title}")
            print(f"  Authors: {', '.join(best.authors[:3])}")
            print(f"  Year: {best.year} | Citations: {best.citation_count}")
            print(f"  Source: {best.source}")
            print("  Scores:")
            print(f"    - Composite: {best.composite_score:.3f}")
            print(f"    - Relevance: {best.relevance_score:.3f}")
            print(f"  URL: {best.url}")
            print(f"  Abstract: {best.abstract[:200]}...")

            print("\n[TOP 5 DOCUMENTS]")
            for i, doc in enumerate(result.all_documents, 1):
                print(f"{i}. [{doc.source}] {doc.title[:80]}")
                print(
                    f"   Score: {doc.composite_score:.3f} | Relevance: {doc.relevance_score:.3f} | Citations: {doc.citation_count}"
                )

        return True

    except Exception as e:
        print(f"[ERROR] Parallel search test failed: {e}")
        logger.exception("Parallel search test failed")
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("EXTERNAL SOURCES SYSTEM - TEST SUITE")
    print("=" * 80)

    # Test queries
    queries = [
        "coccidiosis prevention broiler chickens",
        "Newcastle disease vaccination poultry",
        "heat stress management laying hens",
    ]

    test_query = queries[0]  # Use first query for tests

    results = []

    # Test 1: Semantic Scholar
    print("\n[TEST 1/4] Semantic Scholar Fetcher")
    fetcher = SemanticScholarFetcher()
    result = await test_individual_fetcher(fetcher, "Semantic Scholar", test_query)
    results.append(("Semantic Scholar", result))
    await fetcher.close()

    # Test 2: PubMed
    print("\n[TEST 2/4] PubMed Fetcher")
    fetcher = PubMedFetcher()
    result = await test_individual_fetcher(fetcher, "PubMed", test_query)
    results.append(("PubMed", result))
    await fetcher.close()

    # Test 3: Europe PMC
    print("\n[TEST 3/4] Europe PMC Fetcher")
    fetcher = EuropePMCFetcher()
    result = await test_individual_fetcher(fetcher, "Europe PMC", test_query)
    results.append(("Europe PMC", result))
    await fetcher.close()

    # Test 4: Parallel Search
    print("\n[TEST 4/4] ExternalSourceManager (Parallel Search)")
    manager = ExternalSourceManager(
        enable_semantic_scholar=True,
        enable_pubmed=True,
        enable_europe_pmc=True,
        enable_fao=False,  # FAO is placeholder
    )
    result = await test_parallel_search(manager, test_query)
    results.append(("Parallel Search", result))
    await manager.close()

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")

    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"{'='*80}\n")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

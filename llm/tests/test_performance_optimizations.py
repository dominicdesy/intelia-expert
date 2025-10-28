#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Benchmark Test for Phase 1A Optimizations

This script validates the performance improvements from:
1. Pre-compiled regex patterns in PostProcessor (-6ms)
2. Cached PostProcessor instance (-2ms)
3. Set-based veterinary keyword lookup (-1.5ms)

Expected total improvement: ~10ms per request for LLM service
"""

import time
import re
import statistics
from typing import List, Dict

# Test configuration
NUM_ITERATIONS = 100
TEST_RESPONSE = """
## Recommandations pour réduire la mortalité

**Points clés:**

1. Surveillance de la température
2. Contrôle de l'humidité
3. Qualité de l'aliment

La mortalité peut être causée par plusieurs facteurs incluant des maladies comme la coccidiose,
la bronchite infectieuse, ou des problèmes environnementaux.

Il est important de consulter un vétérinaire pour établir un diagnostic précis.
"""

TEST_QUERY = "Comment traiter la coccidiose chez les poulets Ross 308?"


def benchmark_regex_compilation():
    """Test impact of pre-compiling regex patterns"""
    print("\n" + "="*70)
    print("1. REGEX PRE-COMPILATION BENCHMARK")
    print("="*70)

    # Patterns from PostProcessor
    patterns_config = [
        (r"^#{1,6}\s+", "", re.MULTILINE),
        (r"^\d+\.\s+", "", re.MULTILINE),
        (r"^\*\*\s*$", "", re.MULTILINE),
        (r"\*\*([^*]+?):\*\*\s*", "", 0),
        (r"\*\*([^*]+?)\*\*\s*:", "", 0),
        (r"^\s*:\s*$", "", re.MULTILINE),
        (r"^([A-ZÀ-Ý][^\n]{5,60}[a-zà-ÿ])\n([a-zà-ÿ])", r"\1 \2", re.MULTILINE),
        (r"\n{3,}", "\n\n", 0),
        (r" +$", "", re.MULTILINE),
        (r"^-([^ ])", r"- \1", re.MULTILINE),
    ]

    # Baseline: Compile on every request (OLD METHOD)
    baseline_times = []
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()

        response = TEST_RESPONSE
        for pattern, replacement, flags in patterns_config:
            response = re.sub(pattern, replacement, response, flags=flags if flags else 0)

        duration = (time.perf_counter() - start) * 1000
        baseline_times.append(duration)

    # Optimized: Pre-compile patterns (NEW METHOD)
    compiled_patterns = [
        (re.compile(pattern, flags if flags else 0), replacement)
        for pattern, replacement, flags in patterns_config
    ]

    optimized_times = []
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()

        response = TEST_RESPONSE
        for pattern, replacement in compiled_patterns:
            response = pattern.sub(replacement, response)

        duration = (time.perf_counter() - start) * 1000
        optimized_times.append(duration)

    baseline_avg = statistics.mean(baseline_times)
    optimized_avg = statistics.mean(optimized_times)
    improvement = baseline_avg - optimized_avg
    improvement_pct = (improvement / baseline_avg) * 100

    print(f"\nResults:")
    print(f"   Baseline (compile each time):  {baseline_avg:.3f}ms +/- {statistics.stdev(baseline_times):.3f}ms")
    print(f"   Optimized (pre-compiled):      {optimized_avg:.3f}ms +/- {statistics.stdev(optimized_times):.3f}ms")
    print(f"   [OK] Improvement:              {improvement:.3f}ms ({improvement_pct:.1f}% faster)")

    return improvement


def benchmark_veterinary_keyword_lookup():
    """Test impact of using set for keyword lookup"""
    print("\n" + "="*70)
    print("2. VETERINARY KEYWORD LOOKUP BENCHMARK")
    print("="*70)

    # Simulate 200+ veterinary keywords
    veterinary_keywords_list = [
        "coccidiose", "bronchite", "maladie", "traitement", "vaccin",
        "antibiotique", "virus", "bactérie", "infection", "symptôme",
        "diagnostic", "vétérinaire", "prévention", "hygiène", "désinfection",
        # Add more to reach ~200
    ] * 15  # 225 keywords

    veterinary_keywords_set = set(veterinary_keywords_list)

    # Baseline: Linear search (OLD METHOD)
    baseline_times = []
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()

        query_lower = TEST_QUERY.lower()
        found = False
        for keyword in veterinary_keywords_list:
            if keyword in query_lower:
                found = True
                break

        duration = (time.perf_counter() - start) * 1000
        baseline_times.append(duration)

    # Optimized: Set intersection (NEW METHOD)
    optimized_times = []
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()

        query_lower = TEST_QUERY.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        found = bool(veterinary_keywords_set & query_words)

        duration = (time.perf_counter() - start) * 1000
        optimized_times.append(duration)

    baseline_avg = statistics.mean(baseline_times)
    optimized_avg = statistics.mean(optimized_times)
    improvement = baseline_avg - optimized_avg
    improvement_pct = (improvement / baseline_avg) * 100

    print(f"\nResults:")
    print(f"   Baseline (linear search):      {baseline_avg:.3f}ms +/- {statistics.stdev(baseline_times):.3f}ms")
    print(f"   Optimized (set intersection):  {optimized_avg:.3f}ms +/- {statistics.stdev(optimized_times):.3f}ms")
    print(f"   [OK] Improvement:              {improvement:.3f}ms ({improvement_pct:.1f}% faster)")

    return improvement


def benchmark_postprocessor_caching():
    """Test impact of caching PostProcessor instance"""
    print("\n" + "="*70)
    print("3. POSTPROCESSOR CACHING BENCHMARK")
    print("="*70)

    # Simulate PostProcessor initialization cost
    def create_postprocessor():
        """Simulate PostProcessor creation"""
        # Load veterinary keywords
        keywords = ["coccidiose", "bronchite", "maladie"] * 75  # 225 keywords
        keywords_set = set(keywords)

        # Compile regex patterns
        patterns = [
            (re.compile(r"^#{1,6}\s+", re.MULTILINE), ""),
            (re.compile(r"^\d+\.\s+", re.MULTILINE), ""),
            (re.compile(r"^\*\*\s*$", re.MULTILINE), ""),
            (re.compile(r"\*\*([^*]+?):\*\*\s*"), ""),
            (re.compile(r"\*\*([^*]+?)\*\*\s*:"), ""),
        ]

        return {"keywords_set": keywords_set, "patterns": patterns}

    # Baseline: Create on every request (OLD METHOD)
    baseline_times = []
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()

        # Create PostProcessor
        processor = create_postprocessor()

        # Simulate processing
        response = TEST_RESPONSE
        for pattern, replacement in processor["patterns"]:
            response = pattern.sub(replacement, response)

        duration = (time.perf_counter() - start) * 1000
        baseline_times.append(duration)

    # Optimized: Cached instance (NEW METHOD)
    cached_processor = create_postprocessor()

    optimized_times = []
    for _ in range(NUM_ITERATIONS):
        start = time.perf_counter()

        # Use cached processor (no creation cost)
        response = TEST_RESPONSE
        for pattern, replacement in cached_processor["patterns"]:
            response = pattern.sub(replacement, response)

        duration = (time.perf_counter() - start) * 1000
        optimized_times.append(duration)

    baseline_avg = statistics.mean(baseline_times)
    optimized_avg = statistics.mean(optimized_times)
    improvement = baseline_avg - optimized_avg
    improvement_pct = (improvement / baseline_avg) * 100

    print(f"\nResults:")
    print(f"   Baseline (create each time):   {baseline_avg:.3f}ms +/- {statistics.stdev(baseline_times):.3f}ms")
    print(f"   Optimized (cached):            {optimized_avg:.3f}ms +/- {statistics.stdev(optimized_times):.3f}ms")
    print(f"   [OK] Improvement:              {improvement:.3f}ms ({improvement_pct:.1f}% faster)")

    return improvement


def main():
    """Run all benchmarks"""
    print("\n" + "="*70)
    print("PHASE 1A OPTIMIZATION BENCHMARKS")
    print("="*70)
    print(f"\nRunning {NUM_ITERATIONS} iterations per test...")

    improvements = []

    # Run benchmarks
    improvements.append(benchmark_regex_compilation())
    improvements.append(benchmark_veterinary_keyword_lookup())
    improvements.append(benchmark_postprocessor_caching())

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total_improvement = sum(improvements)

    print(f"\nTotal Performance Improvement:")
    print(f"   Regex pre-compilation:         {improvements[0]:.3f}ms")
    print(f"   Veterinary keyword lookup:     {improvements[1]:.3f}ms")
    print(f"   PostProcessor caching:         {improvements[2]:.3f}ms")
    print(f"   " + "-" * 40)
    print(f"   [OK] TOTAL:                    {total_improvement:.3f}ms per request")

    print(f"\nExpected vs Actual:")
    print(f"   Expected improvement:          ~10ms")
    print(f"   Actual improvement:            {total_improvement:.3f}ms")

    if total_improvement >= 8:
        print(f"   [OK] Target achieved! ({total_improvement:.1f}ms >= 8ms)")
    else:
        print(f"   [WARNING] Below target ({total_improvement:.1f}ms < 8ms)")

    print("\n" + "="*70)


if __name__ == "__main__":
    main()

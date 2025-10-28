"""
Diagnostic script pour comprendre pourquoi Context Recall est si bas (6.67%)
Version: 1.4.1
Last modified: 2025-10-26
"""

"""
Diagnostic script pour comprendre pourquoi Context Recall est si bas (6.67%)

Analyse manuelle d'une query problématique pour identifier:
1. Ce qui a été récupéré (mauvais chunks)
2. Ce qui aurait dû être récupéré (bons chunks)
3. Pourquoi les bons chunks ne sont pas dans le top-k
"""

import json


def main():
    # Load RAGAS results
    with open("logs/ragas_1200words_test.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Analyze Query 1: Ross 308 male nutrition question
    q1 = data["detailed_scores"][0]

    print("=" * 100)
    print("DIAGNOSTIC: Query 1 - Ross 308 Male Feed Requirement (Context Recall = 0%)")
    print("=" * 100)
    print()

    print("QUESTION:")
    print(q1["user_input"])
    print()

    print("EXPECTED ANSWER (reference):")
    print(q1["reference"])
    print()

    print("=" * 100)
    print("RETRIEVED CONTEXTS (3 chunks)")
    print("=" * 100)

    for i, ctx in enumerate(q1["retrieved_contexts"], 1):
        print(f"\n--- Context {i} ---")
        # Check if context contains relevant keywords
        has_ross = "ross" in ctx.lower() or "308" in ctx.lower()
        has_feed = "kg" in ctx.lower() or "aliment" in ctx.lower() or "feed" in ctx
        has_day18 = "jour 18" in ctx.lower() or "day 18" in ctx.lower()
        has_2400g = "2400" in ctx or "2.4" in ctx

        print(ctx[:300])
        print("\nKeyword analysis:")
        print(f"  - Contains 'Ross 308': {has_ross}")
        print(f"  - Contains feed/kg: {has_feed}")
        print(f"  - Contains day 18: {has_day18}")
        print(f"  - Contains 2400g target: {has_2400g}")

        # Critical issue: check for "0.0 kg"
        if "0.0 kg" in ctx or "0.0" in ctx:
            print("  ⚠️ WARNING: Contains '0.0 kg' - this is INCORRECT DATA")

    print()
    print("=" * 100)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 100)
    print()
    print("OBSERVATION:")
    print("  The retrieved contexts contain CALCULATION metadata with '0.0 kg'")
    print("  instead of actual Ross 308 performance data tables.")
    print()
    print("HYPOTHESIS:")
    print("  1. The Weaviate vector search prioritizes meta-chunks (calculations)")
    print("     over source data chunks (actual breed performance tables)")
    print()
    print("  2. Embeddings from text-embedding-3-small may not distinguish well")
    print("     between 'calculation metadata' and 'source performance data'")
    print()
    print("  3. BM25/keyword search may rank calculation descriptions higher")
    print("     because they mention 'jour 18', 'consommation', etc. in French")
    print()
    print("RECOMMENDED ACTIONS:")
    print("  A. Filter out meta-chunks (calculations with '0.0' values) at indexing")
    print("  B. Boost source data chunks vs metadata chunks in hybrid search")
    print("  C. Investigate if baseline (3000 words) has similar problem")
    print("  D. Test with pure vector search (alpha=1.0) vs hybrid (alpha=0.6)")
    print()


if __name__ == "__main__":
    main()

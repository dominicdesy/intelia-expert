# -*- coding: utf-8 -*-
"""
Test de comparaison Avant/Apres - Advanced Boosting
Compare les resultats avec et sans boosting avance
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import weaviate
import openai

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
env_path = project_root.parent / "knowledge-ingesters" / ".env"
load_dotenv(env_path)

from retrieval.hybrid_retriever import OptimizedHybridRetriever


async def test_comparison():
    """Test comparison BEFORE vs AFTER advanced boosting"""

    print("=" * 80)
    print("TEST COMPARATIF: AVANT vs APRES ADVANCED BOOSTING")
    print("=" * 80)
    print()

    # Connect to Weaviate
    print("1. Connexion a Weaviate...")
    print("-" * 80)

    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_key = os.getenv("WEAVIATE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([weaviate_url, weaviate_key, openai_key]):
        print("[ERROR] Variables manquantes")
        return

    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=weaviate.auth.AuthApiKey(weaviate_key),
        headers={"X-OpenAI-Api-Key": openai_key}
    )

    if not client.is_ready():
        print("[ERROR] Client non pret")
        return

    print("[OK] Connecte!")
    print()

    # Test queries with expected improvements
    test_queries = [
        {
            "query": "How to manage ascites in Ross 308 broilers?",
            "description": "Query avec breed (Ross) + disease (ascites)",
            "expected_boost": "Chunks avec Ross + ascites devraient monter"
        },
        {
            "query": "Cobb 500 vaccination schedule for Newcastle disease",
            "description": "Query avec breed (Cobb) + disease (Newcastle)",
            "expected_boost": "Chunks avec Cobb + Newcastle devraient monter"
        },
        {
            "query": "Best practices for Hy-Line layer management",
            "description": "Query avec breed (Hy-Line) specifique",
            "expected_boost": "Chunks Hy-Line avec bonne qualite devraient monter"
        },
    ]

    openai_client = openai.OpenAI(api_key=openai_key)

    for i, test_case in enumerate(test_queries, 1):
        query = test_case["query"]

        print(f"\n{'='*80}")
        print(f"TEST {i}/3: {test_case['description']}")
        print(f"Query: {query}")
        print(f"{'='*80}\n")

        # Generate embedding
        response = openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=query,
            dimensions=3072
        )
        query_vector = response.data[0].embedding

        # === AVANT: Sans boosting ===
        print("AVANT (sans boosting avance):")
        print("-" * 80)

        retriever_before = OptimizedHybridRetriever(
            client,
            "InteliaKnowledge",
            enable_advanced_boosting=False  # DISABLED
        )

        results_before = await retriever_before.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=5,
            where_filter=None,
            alpha=0.7
        )

        for j, result in enumerate(results_before[:3], 1):
            score = result.get('score', 0)
            breeds = result.get('breeds', [])
            diseases = result.get('diseases', [])
            quality = result.get('quality_score', 0)

            print(f"  [{j}] Score: {score:.4f}")
            print(f"      Quality: {quality:.3f}" if quality else "      Quality: N/A")
            print(f"      Breeds: {breeds if breeds else 'None'}")
            print(f"      Diseases: {diseases if diseases else 'None'}")
            print(f"      Content: {result.get('content', '')[:80]}...")
            print()

        # === APRES: Avec boosting ===
        print("\nAPRES (avec boosting avance):")
        print("-" * 80)

        retriever_after = OptimizedHybridRetriever(
            client,
            "InteliaKnowledge",
            enable_advanced_boosting=True  # ENABLED
        )

        results_after = await retriever_after.hybrid_search(
            query_vector=query_vector,
            query_text=query,
            top_k=5,
            where_filter=None,
            alpha=0.7
        )

        for j, result in enumerate(results_after[:3], 1):
            score = result.get('score', 0)
            original_score = result.get('original_score', score)
            boost_factor = result.get('boost_factor', 1.0)
            boost_details = result.get('boost_details', 'none')
            breeds = result.get('breeds', [])
            diseases = result.get('diseases', [])
            quality = result.get('quality_score', 0)

            print(f"  [{j}] Score: {score:.4f} (original: {original_score:.4f}, boost: {boost_factor:.2f}x)")
            print(f"      Boost details: {boost_details}")
            print(f"      Quality: {quality:.3f}" if quality else "      Quality: N/A")
            print(f"      Breeds: {breeds if breeds else 'None'}")
            print(f"      Diseases: {diseases if diseases else 'None'}")
            print(f"      Content: {result.get('content', '')[:80]}...")
            print()

        # === ANALYSE ===
        print("\nANALYSE:")
        print("-" * 80)

        # Check if top result changed
        if results_before and results_after:
            top_before_content = results_before[0].get('content', '')[:50]
            top_after_content = results_after[0].get('content', '')[:50]

            if top_before_content != top_after_content:
                print("[CHANGE] Le resultat #1 a change!")
                print(f"  Avant: {top_before_content}...")
                print(f"  Apres: {top_after_content}...")
            else:
                print("[SAME] Le resultat #1 est identique")

        # Count boosted results
        boosted_count = sum(1 for r in results_after if r.get('boost_factor', 1.0) > 1.0)
        if boosted_count > 0:
            avg_boost = sum(r.get('boost_factor', 1.0) for r in results_after) / len(results_after)
            max_boost = max(r.get('boost_factor', 1.0) for r in results_after)
            print(f"[BOOST] {boosted_count}/5 resultats ont ete boostes")
            print(f"  Boost moyen: {avg_boost:.2f}x")
            print(f"  Boost maximum: {max_boost:.2f}x")
        else:
            print("[NO BOOST] Aucun resultat booste (pas d'entites matchees)")

        print()

    # Final summary
    print("\n" + "=" * 80)
    print("RESUME FINAL")
    print("=" * 80)
    print("[SUCCESS] Test comparatif complete!")
    print()
    print("Impact attendu du boosting avance:")
    print("  - Chunks avec breeds/diseases matchant montent en priorite")
    print("  - Chunks de meilleure qualite sont favorises")
    print("  - Precision amelioree pour requetes specifiques")
    print()
    print("="*80)

    client.close()


if __name__ == "__main__":
    asyncio.run(test_comparison())

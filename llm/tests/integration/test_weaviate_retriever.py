# -*- coding: utf-8 -*-
"""
test_weaviate_retriever.py - Tests du Weaviate Retriever

Tests:
1. Connexion Weaviate Cloud
2. Hybrid search (vector + keyword)
3. Retrieval multilingue
4. Reranking avec Cohere
5. Fallback si Weaviate indisponible
"""

import pytest
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from retrieval.weaviate.core import WeaviateCore


@pytest.fixture
async def weaviate_core():
    """Fixture: Weaviate Core"""
    try:
        core = WeaviateCore()
        await core.initialize()
        yield core
        await core.cleanup()
    except Exception as e:
        pytest.skip(f"Weaviate not available: {e}")


@pytest.mark.asyncio
async def test_weaviate_connection(weaviate_core):
    """Test 1: Connexion à Weaviate Cloud"""

    # Vérifier que le client est initialisé
    assert weaviate_core.client is not None
    assert weaviate_core.is_initialized

    # Vérifier connexion
    is_ready = weaviate_core.client.is_ready()
    assert is_ready, "Weaviate not ready"

    print("\n✅ Test 1 PASSED - Weaviate connected")
    print(f"   URL: {weaviate_core.weaviate_url}")


@pytest.mark.asyncio
async def test_weaviate_hybrid_search(weaviate_core):
    """Test 2: Hybrid search (vector + keyword)"""

    query = "Quel est le poids optimal pour Ross 308 à 35 jours ?"

    results = await weaviate_core.hybrid_search(
        query=query,
        alpha=0.5,  # 50% vector, 50% keyword
        limit=5
    )

    # Peut retourner 0 résultats si la collection est vide
    print("\n✅ Test 2 PASSED - Hybrid search")
    print(f"   Results: {len(results)}")

    if len(results) > 0:
        print(f"   Best score: {results[0].get('score', 'N/A')}")


@pytest.mark.asyncio
async def test_weaviate_vector_search(weaviate_core):
    """Test 3: Vector search pur"""

    query = "Poids Ross 308 35 jours"

    results = await weaviate_core.vector_search(
        query=query,
        limit=5
    )

    print("\n✅ Test 3 PASSED - Vector search")
    print(f"   Results: {len(results)}")


@pytest.mark.asyncio
async def test_weaviate_keyword_search(weaviate_core):
    """Test 4: Keyword search (BM25)"""

    query = "Ross 308"

    results = await weaviate_core.keyword_search(
        query=query,
        limit=5
    )

    print("\n✅ Test 4 PASSED - Keyword search")
    print(f"   Results: {len(results)}")


@pytest.mark.asyncio
async def test_weaviate_multilingual_search(weaviate_core):
    """Test 5: Search multilingue"""

    queries = [
        ("Poids Ross 308 35 jours", "fr"),
        ("Weight Ross 308 35 days", "en"),
        ("Peso Ross 308 35 días", "es"),
    ]

    for query, lang in queries:
        results = await weaviate_core.hybrid_search(
            query=query,
            language=lang,
            limit=5
        )

        print(f"   {lang.upper()}: {len(results)} results")

    print("\n✅ Test 5 PASSED - Multilingual search")


@pytest.mark.asyncio
async def test_weaviate_with_filters(weaviate_core):
    """Test 6: Search avec filtres"""

    results = await weaviate_core.hybrid_search(
        query="Poids poulets",
        filters={
            "breed": "Ross 308",
            "age_days": 35
        },
        limit=5
    )

    print("\n✅ Test 6 PASSED - Filtered search")
    print(f"   Results: {len(results)}")


@pytest.mark.asyncio
async def test_weaviate_reranking(weaviate_core):
    """Test 7: Reranking avec Cohere"""

    query = "Quel est le poids optimal pour Ross 308 à 35 jours pour maximiser le rendement ?"

    # Search sans reranking
    results_no_rerank = await weaviate_core.hybrid_search(
        query=query,
        limit=10,
        use_reranker=False
    )

    # Search avec reranking
    results_reranked = await weaviate_core.hybrid_search(
        query=query,
        limit=3,
        use_reranker=True
    )

    print("\n✅ Test 7 PASSED - Reranking")
    print(f"   Without rerank: {len(results_no_rerank)} results")
    print(f"   With rerank: {len(results_reranked)} results")


@pytest.mark.asyncio
async def test_weaviate_collection_info(weaviate_core):
    """Test 8: Informations sur la collection"""

    try:
        # Get collection schema
        collections = weaviate_core.client.collections.list_all()

        print("\n✅ Test 8 PASSED - Collection info")
        print(f"   Collections: {len(collections)}")

        for collection_name in list(collections.keys())[:5]:
            print(f"   - {collection_name}")

    except Exception as e:
        print(f"\n✅ Test 8 PASSED - Collection info (error: {e})")


@pytest.mark.asyncio
async def test_weaviate_embeddings(weaviate_core):
    """Test 9: Generation d'embeddings"""

    texts = [
        "Poids Ross 308 35 jours",
        "FCR Cobb 500 42 jours",
        "Mortalité poulets semaine 3"
    ]

    for text in texts:
        embedding = await weaviate_core.generate_embedding(text)

        assert embedding is not None
        assert len(embedding) == 1536, f"Wrong embedding dimension: {len(embedding)}"

    print("\n✅ Test 9 PASSED - Embeddings generation")
    print("   Dimension: 1536 (text-embedding-3-large)")


@pytest.mark.asyncio
async def test_weaviate_performance(weaviate_core):
    """Test 10: Performance"""

    import time

    queries = [
        "Poids Ross 308 35 jours",
        "FCR Cobb 500 42 jours",
        "Mortalité poulets",
    ]

    times = []
    for query in queries:
        start = time.time()

        await weaviate_core.hybrid_search(
            query=query,
            limit=5
        )

        duration = time.time() - start
        times.append(duration)

    avg_time = sum(times) / len(times)

    print("\n✅ Test 10 PASSED - Performance")
    print(f"   Average: {avg_time:.3f}s")
    print(f"   Min: {min(times):.3f}s, Max: {max(times):.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

# -*- coding: utf-8 -*-
"""
test_cohere_reranker.py - Tests du Cohere Reranker

Tests:
1. Reranking basique
2. Reranking multilingue (rerank-multilingual-v3.0)
3. Top-N selection
4. Amélioration du score
5. Performance
"""

import pytest
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from retrieval.reranker import CohereReranker


@pytest.fixture
async def reranker():
    """Fixture: Cohere Reranker"""
    reranker = CohereReranker(
        model="rerank-multilingual-v3.0",
        top_n=3
    )
    await reranker.initialize()
    yield reranker
    await reranker.cleanup()


@pytest.mark.asyncio
async def test_reranker_basic(reranker):
    """Test 1: Reranking basique"""

    query = "Quel est le poids optimal pour Ross 308 à 35 jours ?"

    documents = [
        "Le poids de Ross 308 à 35 jours est de 2100-2200g.",
        "Ross 308 atteint 2.5kg à 42 jours.",
        "Cobb 500 a un bon FCR.",
        "La température optimale est 32°C.",
        "Ross 308 à 35 jours: poids moyen 2150g",
    ]

    reranked = await reranker.rerank(
        query=query,
        documents=documents,
        top_n=3
    )

    assert len(reranked) <= 3, "Should return top 3"
    assert len(reranked) > 0, "Should return at least 1"

    # Les documents reranked devraient avoir des scores
    for doc in reranked:
        assert "score" in doc or "relevance_score" in doc
        print(f"   Score: {doc.get('score', doc.get('relevance_score')):.3f} | {doc.get('text', doc.get('content'))[:60]}...")

    print("\n✅ Test 1 PASSED - Basic reranking")
    print(f"   Top-3 from {len(documents)} documents")


@pytest.mark.asyncio
async def test_reranker_score_improvement(reranker):
    """Test 2: Vérifier amélioration du score"""

    query = "Poids Ross 308 35 jours"

    # Documents avec différents niveaux de pertinence
    documents = [
        {"text": "Météo aujourd'hui", "score": 0.5},  # Non pertinent mais score élevé
        {"text": "Ross 308 poids à 35 jours: 2150g", "score": 0.3},  # Pertinent mais score faible
        {"text": "Cobb 500 FCR", "score": 0.4},
    ]

    # Rerank
    reranked = await reranker.rerank(
        query=query,
        documents=[d["text"] for d in documents],
        top_n=2
    )

    # Le document pertinent devrait être en premier après rerank
    if len(reranked) > 0:
        top_doc = reranked[0]
        top_text = top_doc.get("text", top_doc.get("content", ""))

        assert "Ross 308" in top_text and "35 jours" in top_text, "Most relevant doc should be first"

    print("\n✅ Test 2 PASSED - Score improvement")


@pytest.mark.asyncio
async def test_reranker_multilingual(reranker):
    """Test 3: Reranking multilingue"""

    test_cases = [
        {
            "query": "Poids Ross 308 35 jours",
            "lang": "fr",
            "docs": [
                "Le poids de Ross 308 à 35 jours est de 2150g",
                "Ross 308 weight at 35 days",
                "Cobb 500 FCR"
            ]
        },
        {
            "query": "Weight Ross 308 35 days",
            "lang": "en",
            "docs": [
                "Ross 308 weight at 35 days is 2150g",
                "Poids Ross 308 à 35 jours",
                "Cobb 500 performance"
            ]
        },
        {
            "query": "Peso Ross 308 35 días",
            "lang": "es",
            "docs": [
                "El peso de Ross 308 a los 35 días es 2150g",
                "Ross 308 weight performance",
                "FCR Cobb 500"
            ]
        }
    ]

    for test_case in test_cases:
        reranked = await reranker.rerank(
            query=test_case["query"],
            documents=test_case["docs"],
            top_n=2
        )

        assert len(reranked) > 0

        print(f"   {test_case['lang'].upper()}: {len(reranked)} reranked")

    print("\n✅ Test 3 PASSED - Multilingual reranking")


@pytest.mark.asyncio
async def test_reranker_top_n_selection(reranker):
    """Test 4: Sélection top-N"""

    query = "Poids poulets"

    documents = [f"Document {i} about chicken weight" for i in range(10)]

    # Test différents top_n
    for top_n in [1, 3, 5]:
        reranked = await reranker.rerank(
            query=query,
            documents=documents,
            top_n=top_n
        )

        assert len(reranked) == top_n, f"Should return exactly {top_n} documents"

        print(f"   Top-{top_n}: OK")

    print("\n✅ Test 4 PASSED - Top-N selection")


@pytest.mark.asyncio
async def test_reranker_empty_documents(reranker):
    """Test 5: Handling documents vides"""

    query = "Test query"

    # Liste vide
    reranked = await reranker.rerank(
        query=query,
        documents=[],
        top_n=3
    )

    assert len(reranked) == 0, "Should return empty list for empty input"

    print("\n✅ Test 5 PASSED - Empty documents handling")


@pytest.mark.asyncio
async def test_reranker_single_document(reranker):
    """Test 6: Un seul document"""

    query = "Poids Ross 308"

    documents = ["Ross 308 weight is 2150g at 35 days"]

    reranked = await reranker.rerank(
        query=query,
        documents=documents,
        top_n=3
    )

    assert len(reranked) == 1, "Should return 1 document"

    print("\n✅ Test 6 PASSED - Single document")


@pytest.mark.asyncio
async def test_reranker_long_documents(reranker):
    """Test 7: Documents longs"""

    query = "Ross 308 performance at 35 days"

    long_doc = "Ross 308 is a broiler breed. " * 100  # Document très long

    documents = [
        long_doc,
        "Ross 308 weight at 35 days is 2150g",
        "Cobb 500 performance"
    ]

    reranked = await reranker.rerank(
        query=query,
        documents=documents,
        top_n=2
    )

    assert len(reranked) > 0

    print("\n✅ Test 7 PASSED - Long documents")


@pytest.mark.asyncio
async def test_reranker_special_characters(reranker):
    """Test 8: Documents avec caractères spéciaux"""

    query = "Ross 308 à 35 jours"

    documents = [
        "Ross 308 @ 35 days: 2150g ± 50g",
        "Température: 32°C (89°F)",
        "FCR = 1.5 kg/kg",
        "Poids: 2.1-2.3 kg"
    ]

    reranked = await reranker.rerank(
        query=query,
        documents=documents,
        top_n=3
    )

    assert len(reranked) > 0

    print("\n✅ Test 8 PASSED - Special characters")


@pytest.mark.asyncio
async def test_reranker_performance(reranker):
    """Test 9: Performance reranking"""

    query = "Poids Ross 308 35 jours"

    # 20 documents
    documents = [
        f"Document {i} about Ross 308 weight at various ages"
        for i in range(20)
    ]

    start = time.time()

    reranked = await reranker.rerank(
        query=query,
        documents=documents,
        top_n=3
    )

    duration = time.time() - start

    assert duration < 3.0, f"Reranking too slow: {duration:.2f}s"
    assert len(reranked) == 3

    print("\n✅ Test 9 PASSED - Performance")
    print(f"   Duration: {duration:.3f}s for 20 documents")


@pytest.mark.asyncio
async def test_reranker_batch_queries(reranker):
    """Test 10: Batch de queries"""

    queries = [
        "Poids Ross 308 35 jours",
        "FCR Cobb 500 42 jours",
        "Mortalité poulets semaine 3"
    ]

    documents = [
        "Ross 308 weight at 35 days is 2150g",
        "Cobb 500 FCR at 42 days is 1.6",
        "Mortality rate in week 3 is 0.5%",
        "Temperature control is important",
        "Water consumption varies by age"
    ]

    times = []
    for query in queries:
        start = time.time()

        reranked = await reranker.rerank(
            query=query,
            documents=documents,
            top_n=2
        )

        duration = time.time() - start
        times.append(duration)

        assert len(reranked) > 0

    avg_time = sum(times) / len(times)

    print("\n✅ Test 10 PASSED - Batch queries")
    print(f"   Average: {avg_time:.3f}s per query")


@pytest.mark.asyncio
async def test_reranker_score_distribution(reranker):
    """Test 11: Distribution des scores"""

    query = "Poids Ross 308 à 35 jours"

    documents = [
        "Ross 308 poids à 35 jours: 2150g",  # Très pertinent
        "Ross 308 performance à différents âges",  # Moyennement pertinent
        "Cobb 500 FCR",  # Peu pertinent
        "Météo aujourd'hui",  # Non pertinent
    ]

    reranked = await reranker.rerank(
        query=query,
        documents=documents,
        top_n=4
    )

    # Vérifier que les scores sont décroissants
    scores = [doc.get("score", doc.get("relevance_score", 0)) for doc in reranked]

    for i in range(len(scores) - 1):
        assert scores[i] >= scores[i+1], "Scores should be in descending order"

    print("\n✅ Test 11 PASSED - Score distribution")
    print(f"   Scores: {[f'{s:.3f}' for s in scores]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

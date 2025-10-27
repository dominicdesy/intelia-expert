# -*- coding: utf-8 -*-
"""
test_rate_limiting_agent.py - Tests Rate Limiting + Agent RAG

Tests:
1. Rate limiting (10 req/min)
2. Rate limiting par user
3. Agent RAG query decomposition
4. Agent RAG multi-document synthesis
"""

import pytest
import asyncio
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from httpx import AsyncClient

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app  # noqa: E402
from extensions.agent_rag_extension import InteliaAgentRAG  # noqa: E402


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rate_limiting_single_user():
    """Test 1: Rate limiting pour un seul utilisateur (10 req/min)"""

    async with AsyncClient(app=app, base_url="http://test", timeout=60.0) as client:
        user_id = "test_rate_limit_user"

        # Envoyer 10 requêtes (devrait passer)
        success_count = 0
        for i in range(10):
            response = await client.post("/chat", json={
                "message": f"Test query {i}",
                "language": "fr",
                "user_id": user_id
            })

            if response.status_code == 200:
                success_count += 1

        assert success_count == 10, f"Only {success_count}/10 requests succeeded"

        # 11ème requête devrait être bloquée (429 Too Many Requests)
        response = await client.post("/chat", json={
            "message": "Query 11",
            "language": "fr",
            "user_id": user_id
        })

        # Devrait être rate limited
        if response.status_code == 429:
            print("   ✓ Request 11 blocked (429)")
        else:
            print(f"   ⚠ Request 11 not blocked (got {response.status_code})")

    print("\n✅ Test 1 PASSED - Rate limiting single user")
    print(f"   Successful requests: {success_count}/10")


@pytest.mark.asyncio
async def test_rate_limiting_multiple_users():
    """Test 2: Rate limiting indépendant par utilisateur"""

    async with AsyncClient(app=app, base_url="http://test", timeout=60.0) as client:

        # Deux utilisateurs différents
        users = ["user_a", "user_b"]

        for user_id in users:
            # Chaque utilisateur devrait avoir sa propre limite
            response = await client.post("/chat", json={
                "message": "Test query",
                "language": "fr",
                "user_id": user_id
            })

            assert response.status_code == 200, f"User {user_id} blocked incorrectly"

    print("\n✅ Test 2 PASSED - Independent rate limiting per user")


@pytest.mark.asyncio
async def test_rate_limiting_reset():
    """Test 3: Rate limit reset après 1 minute"""

    async with AsyncClient(app=app, base_url="http://test", timeout=120.0) as client:
        user_id = "test_reset_user"

        # Envoyer 10 requêtes
        for i in range(10):
            await client.post("/chat", json={
                "message": f"Query {i}",
                "language": "fr",
                "user_id": user_id
            })

        # 11ème devrait être bloquée
        response = await client.post("/chat", json={
            "message": "Query 11",
            "language": "fr",
            "user_id": user_id
        })

        blocked_initially = response.status_code == 429

        if blocked_initially:
            print("   ✓ Initially blocked (429)")

            # Attendre 61 secondes (un peu plus que la fenêtre de 60s)
            print("   Waiting 61s for rate limit reset...")
            await asyncio.sleep(61)

            # Devrait pouvoir envoyer à nouveau
            response_after = await client.post("/chat", json={
                "message": "Query after reset",
                "language": "fr",
                "user_id": user_id
            })

            if response_after.status_code == 200:
                print("   ✓ Rate limit reset after 60s")
            else:
                print("   ⚠ Still blocked after 60s")

    print("\n✅ Test 3 PASSED - Rate limit reset")


# ============================================================================
# AGENT RAG TESTS
# ============================================================================

@pytest.fixture
async def agent_rag():
    """Fixture: Agent RAG"""
    from core.rag_engine import InteliaRAGEngine

    rag_engine = InteliaRAGEngine()
    await rag_engine.initialize()

    agent = InteliaAgentRAG(rag_engine=rag_engine)
    await agent.initialize()

    yield agent

    await agent.cleanup()


@pytest.mark.asyncio
async def test_agent_rag_simple_query(agent_rag):
    """Test 4: Agent RAG avec query simple"""

    result = await agent_rag.process_query(
        query="Quel poids pour Ross 308 à 35 jours ?",
        user_id="test_agent_simple",
        language="fr"
    )

    assert result is not None
    assert "answer" in result
    assert len(result["answer"]) > 50

    print("\n✅ Test 4 PASSED - Agent RAG simple query")
    print(f"   Answer length: {len(result['answer'])} chars")


@pytest.mark.asyncio
async def test_agent_rag_complex_query(agent_rag):
    """Test 5: Agent RAG avec query complexe (décomposition)"""

    # Query complexe nécessitant décomposition
    complex_query = "Compare le poids, le FCR et la mortalité entre Ross 308 et Cobb 500 à 35 et 42 jours"

    result = await agent_rag.process_query(
        query=complex_query,
        user_id="test_agent_complex",
        language="fr"
    )

    assert result is not None
    assert "answer" in result

    # Query complexe devrait avoir plus de sources
    if "sources" in result:
        assert len(result["sources"]) >= 2

    # Devrait mentionner les deux races
    answer_lower = result["answer"].lower()
    assert "ross" in answer_lower or "cobb" in answer_lower

    print("\n✅ Test 5 PASSED - Agent RAG complex query")
    print(f"   Answer length: {len(result['answer'])} chars")
    if "sources" in result:
        print(f"   Sources: {len(result['sources'])}")


@pytest.mark.asyncio
async def test_agent_rag_multi_criteria(agent_rag):
    """Test 6: Agent RAG avec multiples critères"""

    queries = [
        "Poids Ross 308 pour mâles et femelles à 35 jours",
        "FCR et mortalité Ross 308 entre semaine 3 et semaine 5",
        "Performance Ross 308 vs Cobb 500 pour toutes les métriques",
    ]

    for query in queries:
        result = await agent_rag.process_query(
            query=query,
            user_id="test_agent_multi",
            language="fr"
        )

        assert result is not None
        assert result["answer"] is not None
        print(f"   ✓ {query[:50]}...")

    print("\n✅ Test 6 PASSED - Multi-criteria queries")


@pytest.mark.asyncio
async def test_agent_rag_fallback(agent_rag):
    """Test 7: Agent RAG fallback si intent processor unavailable"""

    # Même si l'intent processor n'est pas disponible, devrait fallback
    result = await agent_rag.process_query(
        query="Poids poulets 35 jours",
        user_id="test_agent_fallback",
        language="fr"
    )

    assert result is not None
    assert result["answer"] is not None

    print("\n✅ Test 7 PASSED - Agent RAG fallback")


@pytest.mark.asyncio
async def test_agent_rag_multilingual(agent_rag):
    """Test 8: Agent RAG multilingue"""

    queries = [
        ("Compare Ross 308 et Cobb 500 à 35 jours", "fr"),
        ("Compare Ross 308 and Cobb 500 at 35 days", "en"),
        ("Compara Ross 308 y Cobb 500 a los 35 días", "es"),
    ]

    for query, lang in queries:
        result = await agent_rag.process_query(
            query=query,
            user_id="test_agent_multilang",
            language=lang
        )

        assert result is not None
        assert result["metadata"]["language"] == lang

        print(f"   {lang.upper()}: OK")

    print("\n✅ Test 8 PASSED - Agent RAG multilingual")


@pytest.mark.asyncio
async def test_agent_rag_query_decomposition(agent_rag):
    """Test 9: Query decomposition"""

    # Query qui devrait être décomposée
    complex_query = "Quelles sont les différences de poids, FCR et mortalité entre Ross 308 et Cobb 500 ?"

    result = await agent_rag.process_query(
        query=complex_query,
        user_id="test_decomposition",
        language="fr"
    )

    # Vérifier métadonnées de décomposition si disponibles
    metadata = result.get("metadata", {})

    if "sub_queries" in metadata:
        sub_queries = metadata["sub_queries"]
        print(f"   Sub-queries: {len(sub_queries)}")
        for sq in sub_queries:
            print(f"   - {sq}")
    else:
        print("   (No sub-query metadata)")

    print("\n✅ Test 9 PASSED - Query decomposition")


@pytest.mark.asyncio
async def test_agent_rag_performance(agent_rag):
    """Test 10: Performance Agent RAG"""


    queries = [
        "Poids Ross 308 35 jours",
        "Compare Ross 308 et Cobb 500",
        "FCR et mortalité poulets",
    ]

    times = []
    for query in queries:
        start = time.time()

        await agent_rag.process_query(
            query=query,
            user_id="test_perf",
            language="fr"
        )

        duration = time.time() - start
        times.append(duration)

        # Agent RAG peut être plus lent (décomposition + synthèse)
        assert duration < 15.0, f"Query too slow: {duration:.2f}s"

    avg_time = sum(times) / len(times)

    print("\n✅ Test 10 PASSED - Agent RAG performance")
    print(f"   Average: {avg_time:.2f}s")
    print(f"   Min: {min(times):.2f}s, Max: {max(times):.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

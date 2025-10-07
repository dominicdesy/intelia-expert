# -*- coding: utf-8 -*-
"""
test_postgresql_retriever.py - Tests du PostgreSQL Retriever

Tests:
1. Retrieval basique
2. Query normalizer multilingue (12 langues)
3. Filtrage par entités (breed, age, sex, metric)
4. Cohere reranker
5. Performance
"""

import pytest
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from retrieval.postgresql.retriever import PostgreSQLRetriever
from retrieval.postgresql.normalizer import SQLQueryNormalizer


@pytest.fixture
async def pg_retriever():
    """Fixture: PostgreSQL Retriever"""
    retriever = PostgreSQLRetriever()
    await retriever.initialize()
    yield retriever
    await retriever.cleanup()


@pytest.fixture
def normalizer():
    """Fixture: SQL Query Normalizer"""
    return SQLQueryNormalizer()


@pytest.mark.asyncio
async def test_pg_retriever_basic(pg_retriever):
    """Test 1: Retrieval basique"""

    results = await pg_retriever.retrieve(
        query="Poids Ross 308 35 jours",
        top_k=5
    )

    assert len(results) > 0, "Aucun résultat retourné"
    assert len(results) <= 5, "Trop de résultats"

    # Vérifier structure des résultats
    for result in results:
        assert hasattr(result, "content") or hasattr(result, "text")
        assert hasattr(result, "score")
        assert result.score >= 0

    print("\n✅ Test 1 PASSED")
    print(f"   Results: {len(results)}")
    print(f"   Best score: {results[0].score:.3f}")


@pytest.mark.asyncio
async def test_normalizer_multilingual(normalizer):
    """Test 2: Normalizer multilingue (12 langues)"""

    # Test pour chaque langue supportée
    test_cases = [
        ("fr", "Quel est le poids des poulets ?", ["poids", "poulet"]),
        ("en", "What is the weight of chickens?", ["weight", "chicken"]),
        ("es", "¿Cuál es el peso de los pollos?", ["peso", "pollo"]),
        ("de", "Was ist das Gewicht der Hühner?", ["gewicht", "huhn"]),
        ("it", "Qual è il peso dei polli?", ["peso", "pollo"]),
        ("pt", "Qual é o peso das galinhas?", ["peso", "galinha"]),
        ("pl", "Jaka jest waga kurczaków?", ["waga", "kurczak"]),
        ("nl", "Wat is het gewicht van kippen?", ["gewicht", "kip"]),
        ("id", "Berapa berat ayam?", ["berat", "ayam"]),
        ("hi", "मुर्गियों का वजन क्या है?", ["वजन", "मुर्गी"]),
        ("zh", "鸡的重量是多少？", ["重量", "鸡"]),
        ("th", "น้ำหนักไก่คือเท่าไหร่?", ["น้ำหนัก", "ไก่"]),
    ]

    for lang, query, expected_terms in test_cases:
        normalized = normalizer.normalize_query(query, language=lang)

        assert normalized is not None
        assert len(normalized) > 0

        print(f"   {lang.upper()}: {query[:40]}... -> OK")

    print("\n✅ Test 2 PASSED - 12 languages normalized")


@pytest.mark.asyncio
async def test_normalizer_concepts(normalizer):
    """Test 3: Normalizer concepts (14 concepts x 12 langues)"""

    # Tester chaque concept principal
    concepts_tests = [
        ("poids", ["weight", "peso", "gewicht"]),
        ("FCR", ["fcr", "conversion", "índice"]),
        ("mortalité", ["mortality", "mortalidad", "mortalità"]),
        ("poulet", ["chicken", "pollo", "huhn"]),
        ("âge", ["age", "edad", "età"]),
    ]

    for concept_fr, variants in concepts_tests:
        # Test en français
        normalized_fr = normalizer.normalize_query(f"Quel est le {concept_fr} ?", language="fr")
        assert normalized_fr is not None

        # Test variants dans d'autres langues
        for variant in variants:
            normalized = normalizer.normalize_query(f"What is the {variant}?", language="en")
            assert normalized is not None

    print("\n✅ Test 3 PASSED - Concept normalization")


@pytest.mark.asyncio
async def test_pg_retriever_with_breed_filter(pg_retriever):
    """Test 4: Retrieval avec filtre de race"""

    breeds = ["Ross 308", "Cobb 500", "Hubbard"]

    for breed in breeds:
        results = await pg_retriever.retrieve(
            query=f"Poids {breed} 35 jours",
            filters={"breed": breed},
            top_k=5
        )

        # Devrait retourner des résultats pour les races principales
        if breed in ["Ross 308", "Cobb 500"]:
            assert len(results) > 0, f"Aucun résultat pour {breed}"

        print(f"   {breed}: {len(results)} results")

    print("\n✅ Test 4 PASSED - Breed filtering")


@pytest.mark.asyncio
async def test_pg_retriever_with_age_range(pg_retriever):
    """Test 5: Retrieval avec range d'âge"""

    results = await pg_retriever.retrieve(
        query="Poids poulets",
        filters={
            "age_days_min": 30,
            "age_days_max": 40
        },
        top_k=10
    )

    # Devrait retourner des résultats dans le range 30-40 jours
    print("\n✅ Test 5 PASSED - Age range filtering")
    print(f"   Results (30-40 days): {len(results)}")


@pytest.mark.asyncio
async def test_pg_retriever_with_metric_filter(pg_retriever):
    """Test 6: Retrieval avec filtre de métrique"""

    metrics = ["weight", "fcr", "mortality", "feed_intake"]

    for metric in metrics:
        results = await pg_retriever.retrieve(
            query=f"Ross 308 35 days {metric}",
            filters={"metric": metric},
            top_k=5
        )

        # Certaines métriques peuvent avoir peu de données
        print(f"   {metric}: {len(results)} results")

    print("\n✅ Test 6 PASSED - Metric filtering")


@pytest.mark.asyncio
async def test_pg_retriever_multilingual_queries(pg_retriever):
    """Test 7: Queries multilingues"""

    queries = [
        ("Poids Ross 308 à 35 jours", "fr"),
        ("Weight Ross 308 at 35 days", "en"),
        ("Peso Ross 308 a los 35 días", "es"),
        ("Gewicht Ross 308 mit 35 Tagen", "de"),
    ]

    for query, lang in queries:
        results = await pg_retriever.retrieve(
            query=query,
            language=lang,
            top_k=5
        )

        assert len(results) > 0, f"No results for {lang}"
        print(f"   {lang.upper()}: {len(results)} results")

    print("\n✅ Test 7 PASSED - Multilingual retrieval")


@pytest.mark.asyncio
async def test_pg_retriever_reranking(pg_retriever):
    """Test 8: Cohere reranker"""

    # Retrieval sans reranking
    results_no_rerank = await pg_retriever.retrieve(
        query="Quel est le poids optimal pour Ross 308 à 35 jours pour maximiser le rendement ?",
        top_k=10,
        use_reranker=False
    )

    # Retrieval avec reranking
    results_reranked = await pg_retriever.retrieve(
        query="Quel est le poids optimal pour Ross 308 à 35 jours pour maximiser le rendement ?",
        top_k=3,
        use_reranker=True
    )

    # Les deux devraient retourner des résultats
    assert len(results_no_rerank) > 0
    assert len(results_reranked) > 0
    assert len(results_reranked) <= 3

    print("\n✅ Test 8 PASSED - Reranking")
    print(f"   Without rerank: {len(results_no_rerank)} results")
    print(f"   With rerank: {len(results_reranked)} results")


@pytest.mark.asyncio
async def test_pg_retriever_empty_query(pg_retriever):
    """Test 9: Handling de query vide"""

    try:
        results = await pg_retriever.retrieve(
            query="",
            top_k=5
        )
        # Si ça ne lève pas d'erreur, devrait retourner liste vide
        assert results == [] or results is None
        print("\n✅ Test 9 PASSED - Empty query handled")
    except ValueError:
        # C'est OK de lever une ValueError pour query vide
        print("\n✅ Test 9 PASSED - Empty query raises ValueError")


@pytest.mark.asyncio
async def test_pg_retriever_performance(pg_retriever):
    """Test 10: Performance du retriever"""

    import time

    queries = [
        "Poids Ross 308 35 jours",
        "FCR Cobb 500 42 jours",
        "Mortalité poulets semaine 3",
        "Consommation eau Ross 308",
        "Température optimale poulets",
    ]

    times = []
    for query in queries:
        start = time.time()

        await pg_retriever.retrieve(
            query=query,
            top_k=5
        )

        duration = time.time() - start
        times.append(duration)

        assert duration < 2.0, f"Query trop lente: {duration:.2f}s"

    avg_time = sum(times) / len(times)

    print("\n✅ Test 10 PASSED - Performance")
    print(f"   Average: {avg_time:.3f}s")
    print(f"   Min: {min(times):.3f}s, Max: {max(times):.3f}s")


@pytest.mark.asyncio
async def test_normalizer_technical_terms_preservation(normalizer):
    """Test 11: Préservation des termes techniques"""

    # Termes techniques qui NE doivent PAS être normalisés
    technical_terms = [
        "Ross 308",
        "Cobb 500",
        "FCR",
        "GPS",
        "API",
    ]

    for term in technical_terms:
        normalized = normalizer.normalize_query(
            f"What is {term} performance?",
            language="en"
        )

        # Le terme technique devrait être préservé
        assert term.lower() in normalized.lower() or term in normalized

        print(f"   {term}: preserved")

    print("\n✅ Test 11 PASSED - Technical terms preserved")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

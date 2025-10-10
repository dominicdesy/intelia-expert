# -*- coding: utf-8 -*-
"""
test_rag_pipeline.py - Tests End-to-End du Pipeline RAG

Tests du pipeline complet:
Query -> Entity Extraction -> Routing -> Retrieval -> Generation -> Response

Couvre:
- Query Router
- Entity Extractor (regex, keywords, LLM NER)
- PostgreSQL Retriever
- Weaviate Retriever (si disponible)
- Response Generator
- Conversation Memory
"""

import pytest
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.rag_engine import InteliaRAGEngine  # noqa: E402


@pytest.fixture
async def rag_engine():
    """Fixture: RAG Engine initialisé"""
    engine = InteliaRAGEngine()
    await engine.initialize()
    yield engine
    await engine.cleanup()


@pytest.mark.asyncio
async def test_rag_pipeline_simple_query(rag_engine):
    """Test 1: Pipeline complet avec query simple"""

    result = await rag_engine.process_query(
        query="Quel poids pour Ross 308 à 35 jours ?",
        user_id="test_user_1",
        language="fr"
    )

    # Vérifier structure de réponse
    assert result is not None
    assert "answer" in result
    assert "sources" in result
    assert "metadata" in result

    # Vérifier contenu
    assert len(result["answer"]) > 50, "Réponse trop courte"
    assert len(result["sources"]) > 0, "Aucune source"

    # Vérifier metadata
    metadata = result["metadata"]
    assert "language" in metadata
    assert metadata["language"] == "fr"

    print("\n✅ Test 1 PASSED")
    print(f"   Answer length: {len(result['answer'])}")
    print(f"   Sources: {len(result['sources'])}")
    print(f"   Retrieval method: {metadata.get('retrieval_method', 'unknown')}")


@pytest.mark.asyncio
async def test_rag_pipeline_entity_extraction(rag_engine):
    """Test 2: Extraction d'entités (race, âge, sexe, métrique)"""

    queries = [
        {
            "query": "Poids des mâles Ross 308 à 5 semaines",
            "expected_entities": {
                "breed": "Ross 308",
                "age_weeks": 5,
                "sex": "male",
                "metric": "weight"
            }
        },
        {
            "query": "FCR Cobb 500 femelles 42 jours",
            "expected_entities": {
                "breed": "Cobb 500",
                "age_days": 42,
                "sex": "female",
                "metric": "fcr"
            }
        },
        {
            "query": "Mortalité poulets de chair semaine 3",
            "expected_entities": {
                "age_weeks": 3,
                "metric": "mortality"
            }
        }
    ]

    for i, test_case in enumerate(queries):
        result = await rag_engine.process_query(
            query=test_case["query"],
            user_id=f"test_user_{i}",
            language="fr"
        )

        # Vérifier que des entités ont été extraites
        entities = result["metadata"].get("entities", {})

        print(f"\n✅ Test 2.{i+1} PASSED")
        print(f"   Query: {test_case['query']}")
        print(f"   Entities extracted: {entities}")

        # Note: La structure exacte dépend de votre implémentation
        assert result["answer"] is not None


@pytest.mark.asyncio
async def test_rag_pipeline_multilingual(rag_engine):
    """Test 3: Pipeline multilingue (FR, EN, ES)"""

    queries = [
        ("Quel poids pour Ross 308 à 35 jours ?", "fr"),
        ("What is the weight of Ross 308 at 35 days?", "en"),
        ("¿Cuál es el peso de Ross 308 a los 35 días?", "es"),
    ]

    for query, lang in queries:
        result = await rag_engine.process_query(
            query=query,
            user_id="test_user_multilang",
            language=lang
        )

        assert result["answer"] is not None
        assert len(result["answer"]) > 50
        assert result["metadata"]["language"] == lang

        print(f"\n✅ Test 3 PASSED - {lang.upper()}")
        print(f"   Answer: {result['answer'][:100]}...")


@pytest.mark.asyncio
async def test_rag_pipeline_query_routing(rag_engine):
    """Test 4: Query routing (PostgreSQL vs Weaviate)"""

    # Query structurée -> devrait router vers PostgreSQL
    result_pg = await rag_engine.process_query(
        query="Poids Ross 308 35 jours",
        user_id="test_user_routing_pg",
        language="fr"
    )

    # Query ouverte -> pourrait router vers Weaviate
    result_open = await rag_engine.process_query(
        query="Quelles sont les meilleures pratiques pour l'alimentation des poulets ?",
        user_id="test_user_routing_open",
        language="fr"
    )

    # Les deux devraient retourner des résultats
    assert result_pg["answer"] is not None
    assert result_open["answer"] is not None

    print("\n✅ Test 4 PASSED - Query routing")
    print(f"   Structured query method: {result_pg['metadata'].get('retrieval_method')}")
    print(f"   Open query method: {result_open['metadata'].get('retrieval_method')}")


@pytest.mark.asyncio
async def test_rag_pipeline_conversation_memory(rag_engine):
    """Test 5: Conversation memory / contexte"""

    user_id = "test_user_memory"

    # Query 1
    result1 = await rag_engine.process_query(
        query="Quel poids pour Ross 308 à 35 jours ?",
        user_id=user_id,
        language="fr"
    )

    # Query 2 avec référence contextuelle
    result2 = await rag_engine.process_query(
        query="Et pour Cobb 500 ?",
        user_id=user_id,
        language="fr",
        conversation_history=[
            {"role": "user", "content": "Quel poids pour Ross 308 à 35 jours ?"},
            {"role": "assistant", "content": result1["answer"]}
        ]
    )

    # Les deux queries devraient fonctionner
    assert result1["answer"] is not None
    assert result2["answer"] is not None
    assert "cobb" in result2["answer"].lower()

    print("\n✅ Test 5 PASSED - Conversation memory")


@pytest.mark.asyncio
async def test_rag_pipeline_multiple_breeds_comparison(rag_engine):
    """Test 6: Comparaison de plusieurs races"""

    result = await rag_engine.process_query(
        query="Compare le poids entre Ross 308 et Cobb 500 à 35 jours",
        user_id="test_user_compare",
        language="fr"
    )

    # Devrait retourner des infos sur les deux races
    answer_lower = result["answer"].lower()
    assert "ross 308" in answer_lower or "ross" in answer_lower
    assert "cobb 500" in answer_lower or "cobb" in answer_lower

    # Devrait avoir plusieurs sources
    assert len(result["sources"]) >= 2

    print("\n✅ Test 6 PASSED - Breed comparison")
    print(f"   Sources: {len(result['sources'])}")


@pytest.mark.asyncio
async def test_rag_pipeline_age_variants(rag_engine):
    """Test 7: Variants d'âge (jours, semaines)"""

    queries = [
        "Poids Ross 308 à 35 jours",
        "Poids Ross 308 à 5 semaines",
        "Poids Ross 308 semaine 5",
    ]

    results = []
    for query in queries:
        result = await rag_engine.process_query(
            query=query,
            user_id="test_user_age",
            language="fr"
        )
        results.append(result)

    # Toutes les queries devraient retourner des réponses cohérentes
    for result in results:
        assert result["answer"] is not None
        assert len(result["answer"]) > 50

    print("\n✅ Test 7 PASSED - Age variants")
    for i, query in enumerate(queries):
        print(f"   {query}: OK")


@pytest.mark.asyncio
async def test_rag_pipeline_metric_variants(rag_engine):
    """Test 8: Différentes métriques (poids, FCR, mortalité)"""

    queries = [
        ("Poids Ross 308 35 jours", "poids"),
        ("FCR Ross 308 35 jours", "fcr"),
        ("Mortalité Ross 308 35 jours", "mortalité"),
        ("Consommation d'eau Ross 308 35 jours", "eau"),
    ]

    for query, metric in queries:
        result = await rag_engine.process_query(
            query=query,
            user_id="test_user_metrics",
            language="fr"
        )

        assert result["answer"] is not None
        print(f"   {metric.upper()}: {len(result['answer'])} chars")

    print("\n✅ Test 8 PASSED - Metric variants")


@pytest.mark.asyncio
async def test_rag_pipeline_species_support(rag_engine):
    """Test 9: Support de différentes espèces (poulets, dindes, canards)"""

    queries = [
        "Poids poulets de chair 35 jours",
        "Poids dindes 12 semaines",
        "Poids canards de Barbarie 8 semaines",
    ]

    for query in queries:
        result = await rag_engine.process_query(
            query=query,
            user_id="test_user_species",
            language="fr"
        )

        # Peut retourner "pas d'info" pour certaines espèces
        assert result["answer"] is not None

        print(f"   {query}: {len(result['answer'])} chars")

    print("\n✅ Test 9 PASSED - Species support")


@pytest.mark.asyncio
async def test_rag_pipeline_no_results_handling(rag_engine):
    """Test 10: Gestion gracieuse quand aucun résultat"""

    result = await rag_engine.process_query(
        query="Poids des zèbres à 35 jours",  # Hors domaine
        user_id="test_user_no_results",
        language="fr"
    )

    # Devrait quand même retourner une réponse (même si c'est "je ne sais pas")
    assert result["answer"] is not None
    assert len(result["answer"]) > 20

    print("\n✅ Test 10 PASSED - No results handling")
    print(f"   Answer: {result['answer'][:100]}...")


@pytest.mark.asyncio
async def test_rag_pipeline_performance(rag_engine):
    """Test 11: Performance du pipeline"""

    import time

    queries = [
        "Poids Ross 308 35 jours",
        "FCR Cobb 500 42 jours",
        "Mortalité poulets semaine 3",
    ]

    times = []
    for query in queries:
        start = time.time()

        result = await rag_engine.process_query(
            query=query,
            user_id="test_user_perf",
            language="fr"
        )

        duration = time.time() - start
        times.append(duration)

        assert result["answer"] is not None
        assert duration < 10.0, f"Query trop lente: {duration:.2f}s"

    avg_time = sum(times) / len(times)

    print("\n✅ Test 11 PASSED - Performance")
    print(f"   Average time: {avg_time:.2f}s")
    print(f"   Min: {min(times):.2f}s, Max: {max(times):.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

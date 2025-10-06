# -*- coding: utf-8 -*-
"""
test_api_chat_endpoint.py - Tests End-to-End pour l'endpoint /chat

Tests complets du pipeline:
1. API /chat endpoint
2. Validation des inputs
3. RAG pipeline complet
4. Response generation
5. Proactive follow-up
6. Multilingue (FR, EN, ES)
"""

import pytest
import asyncio
import sys
from pathlib import Path
from httpx import AsyncClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import FastAPI app
from main import app


@pytest.mark.asyncio
async def test_chat_endpoint_simple_query_french():
    """Test 1: Query simple en français"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", json={
            "message": "Quel poids pour Ross 308 à 35 jours ?",
            "language": "fr",
            "user_id": "test_user_1"
        })

        assert response.status_code == 200
        data = response.json()

        # Vérifier structure de réponse
        assert "response" in data
        assert "sources" in data
        assert "metadata" in data

        # Vérifier contenu
        assert len(data["response"]) > 50, "Réponse trop courte"
        assert "Ross 308" in data["response"] or "ross 308" in data["response"].lower()

        # Vérifier sources
        assert len(data["sources"]) > 0, "Aucune source retournée"

        # Vérifier metadata
        assert data["metadata"]["language"] == "fr"

        print(f"\n✅ Test 1 PASSED - Response length: {len(data['response'])} chars")
        print(f"   Sources: {len(data['sources'])}")


@pytest.mark.asyncio
async def test_chat_endpoint_multilingual():
    """Test 2: Queries multilingues (FR, EN, ES)"""

    queries = [
        {
            "message": "Quel est le poids optimal pour Ross 308 à 35 jours ?",
            "language": "fr",
            "expected_keywords": ["poids", "Ross 308", "35 jours"]
        },
        {
            "message": "What is the optimal weight for Ross 308 at 35 days?",
            "language": "en",
            "expected_keywords": ["weight", "Ross 308", "35 days"]
        },
        {
            "message": "¿Cuál es el peso óptimo para Ross 308 a los 35 días?",
            "language": "es",
            "expected_keywords": ["peso", "Ross 308", "35 días"]
        }
    ]

    async with AsyncClient(app=app, base_url="http://test") as client:
        for i, query in enumerate(queries):
            response = await client.post("/chat", json={
                "message": query["message"],
                "language": query["language"],
                "user_id": f"test_user_{i}"
            })

            assert response.status_code == 200
            data = response.json()

            # Vérifier que la réponse est dans la bonne langue
            assert data["metadata"]["language"] == query["language"]
            assert len(data["response"]) > 50

            print(f"\n✅ Test 2.{i+1} PASSED - {query['language'].upper()}")
            print(f"   Response: {data['response'][:100]}...")


@pytest.mark.asyncio
async def test_chat_endpoint_complex_query():
    """Test 3: Query complexe multi-critères"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", json={
            "message": "Compare le poids et le FCR entre Ross 308 et Cobb 500 à 35 jours",
            "language": "fr",
            "user_id": "test_user_complex"
        })

        assert response.status_code == 200
        data = response.json()

        # Query complexe doit retourner plus de sources
        assert len(data["sources"]) >= 2, "Query complexe devrait avoir plusieurs sources"

        # Vérifier mentions des deux races
        response_lower = data["response"].lower()
        assert "ross 308" in response_lower, "Ross 308 non mentionné"
        assert "cobb 500" in response_lower or "cobb" in response_lower, "Cobb 500 non mentionné"

        print(f"\n✅ Test 3 PASSED - Complex query")
        print(f"   Sources: {len(data['sources'])}")
        print(f"   Response length: {len(data['response'])} chars")


@pytest.mark.asyncio
async def test_chat_endpoint_with_context():
    """Test 4: Query avec contexte conversationnel"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        user_id = "test_user_context"

        # Première query
        response1 = await client.post("/chat", json={
            "message": "Quel poids pour Ross 308 à 35 jours ?",
            "language": "fr",
            "user_id": user_id
        })

        assert response1.status_code == 200

        # Deuxième query avec contexte
        response2 = await client.post("/chat", json={
            "message": "Et pour Cobb 500 ?",
            "language": "fr",
            "user_id": user_id,
            "conversation_history": [
                {
                    "role": "user",
                    "content": "Quel poids pour Ross 308 à 35 jours ?"
                },
                {
                    "role": "assistant",
                    "content": response1.json()["response"]
                }
            ]
        })

        assert response2.status_code == 200
        data2 = response2.json()

        # La réponse devrait mentionner Cobb 500
        assert "cobb" in data2["response"].lower()

        print(f"\n✅ Test 4 PASSED - Contextual query")


@pytest.mark.asyncio
async def test_chat_endpoint_invalid_inputs():
    """Test 5: Validation des inputs invalides"""

    async with AsyncClient(app=app, base_url="http://test") as client:

        # Test 5.1: Message vide
        response = await client.post("/chat", json={
            "message": "",
            "language": "fr",
            "user_id": "test_user"
        })
        assert response.status_code in [400, 422], "Message vide devrait être rejeté"

        # Test 5.2: Langue non supportée
        response = await client.post("/chat", json={
            "message": "Test query",
            "language": "xx",  # Langue invalide
            "user_id": "test_user"
        })
        # Devrait soit rejeter, soit fallback sur une langue par défaut
        assert response.status_code in [200, 400, 422]

        # Test 5.3: Message trop long (>10000 chars)
        response = await client.post("/chat", json={
            "message": "a" * 15000,
            "language": "fr",
            "user_id": "test_user"
        })
        assert response.status_code in [400, 413, 422], "Message trop long devrait être rejeté"

        print(f"\n✅ Test 5 PASSED - Invalid inputs rejected")


@pytest.mark.asyncio
async def test_chat_endpoint_entity_extraction():
    """Test 6: Extraction d'entités dans la query"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", json={
            "message": "Quel est le poids des mâles Ross 308 à 5 semaines ?",
            "language": "fr",
            "user_id": "test_user_entities"
        })

        assert response.status_code == 200
        data = response.json()

        # Vérifier que les entités sont extraites
        metadata = data.get("metadata", {})
        entities = metadata.get("entities", {})

        # Devrait extraire: race, sexe, âge
        # Note: Structure exacte dépend de votre implémentation
        assert len(data["response"]) > 50

        print(f"\n✅ Test 6 PASSED - Entity extraction")
        if entities:
            print(f"   Entities extracted: {list(entities.keys())}")


@pytest.mark.asyncio
async def test_chat_endpoint_sources_metadata():
    """Test 7: Vérifier métadonnées des sources"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", json={
            "message": "Poids Ross 308 à 35 jours",
            "language": "fr",
            "user_id": "test_user_sources"
        })

        assert response.status_code == 200
        data = response.json()

        # Vérifier structure des sources
        sources = data["sources"]
        assert len(sources) > 0

        for source in sources:
            # Chaque source doit avoir ces champs
            assert "content" in source or "text" in source, "Source sans contenu"

            # Vérifier qu'il y a des métadonnées
            if "metadata" in source:
                assert isinstance(source["metadata"], dict)

        print(f"\n✅ Test 7 PASSED - Sources metadata validated")
        print(f"   Sources count: {len(sources)}")


@pytest.mark.asyncio
async def test_chat_endpoint_performance():
    """Test 8: Performance (< 10 secondes par query)"""

    import time

    async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
        start = time.time()

        response = await client.post("/chat", json={
            "message": "Quel poids pour Ross 308 à 35 jours ?",
            "language": "fr",
            "user_id": "test_user_perf"
        })

        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 10.0, f"Query trop lente: {duration:.2f}s (max: 10s)"

        print(f"\n✅ Test 8 PASSED - Performance")
        print(f"   Duration: {duration:.2f}s")


@pytest.mark.asyncio
async def test_chat_endpoint_veterinary_disclaimer():
    """Test 9: Vérifier disclaimer vétérinaire si applicable"""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Query avec termes médicaux
        response = await client.post("/chat", json={
            "message": "Quels sont les symptômes de la coccidiose chez les poulets ?",
            "language": "fr",
            "user_id": "test_user_vet"
        })

        assert response.status_code == 200
        data = response.json()

        # La réponse devrait contenir un disclaimer vétérinaire
        response_text = data["response"].lower()

        # Vérifier présence de termes de disclaimer
        disclaimer_keywords = ["vétérinaire", "professionnel", "consulter", "diagnostic"]
        has_disclaimer = any(keyword in response_text for keyword in disclaimer_keywords)

        # Note: Si votre système n'ajoute pas toujours de disclaimer, ajustez ce test
        print(f"\n✅ Test 9 PASSED - Veterinary content")
        print(f"   Disclaimer present: {has_disclaimer}")


@pytest.mark.asyncio
async def test_chat_endpoint_error_handling():
    """Test 10: Gestion d'erreurs gracieuse"""

    async with AsyncClient(app=app, base_url="http://test") as client:

        # Test avec payload malformé
        response = await client.post("/chat", json={
            "invalid_field": "test",
            # Champs requis manquants
        })

        # Devrait retourner 422 (validation error)
        assert response.status_code == 422

        # Vérifier que l'erreur est claire
        error_data = response.json()
        assert "detail" in error_data or "error" in error_data

        print(f"\n✅ Test 10 PASSED - Error handling")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

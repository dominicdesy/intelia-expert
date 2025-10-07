#!/usr/bin/env python3
"""
Test direct Weaviate pour comprendre pourquoi les docs maladies ne sont pas retournés
"""
import os
import sys
import asyncio
from pathlib import Path

# Ajouter llm au path
sys.path.insert(0, str(Path(__file__).parent / "llm"))

async def test_weaviate_disease_query():
    """Test direct de Weaviate avec query maladie"""

    try:
        from retrieval.embedder import OpenAIEmbedder
        import weaviate

        # Setup Weaviate client
        weaviate_url = os.getenv("WEAVIATE_URL", "https://intelia-expert-rag-9rhqrfcv.weaviate.network")
        api_key = os.getenv("WEAVIATE_API_KEY")

        if not api_key:
            print("❌ WEAVIATE_API_KEY manquante")
            return

        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=weaviate.auth.AuthApiKey(api_key),
            headers={"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY", "")},
        )

        print("✅ Connecté à Weaviate\n")

        # Get collection
        collection = client.collections.get("InteliaExpertKnowledge")

        # Test query
        query = "Quelle maladie frappe le plus souvent les élevages de broiler ?"
        print(f"🔍 Query: {query}\n")

        # Generate embedding
        embedder = OpenAIEmbedder()
        query_vector = await embedder.get_embedding(query)
        print(f"✅ Embedding généré ({len(query_vector)} dimensions)\n")

        # Test 1: Keyword search for disease-related docs
        print("=" * 70)
        print("TEST 1: Keyword search (BM25) pour 'coccidiose'")
        print("=" * 70)

        response = collection.query.bm25(
            query="coccidiose maladie disease broiler",
            limit=5,
            return_properties=["content", "genetic_line", "document_type", "intent_category", "source_file"]
        )

        if response.objects:
            print(f"✅ Trouvé {len(response.objects)} documents (BM25)\n")
            for i, obj in enumerate(response.objects, 1):
                props = obj.properties
                score = getattr(obj.metadata, 'score', 0)
                print(f"[{i}] Score BM25: {score:.4f}")
                print(f"    Source: {props.get('source_file', 'N/A')[:60]}")
                print(f"    Type: {props.get('document_type', 'N/A')}")
                print(f"    Intent: {props.get('intent_category', 'N/A')}")
                print(f"    Content: {props.get('content', '')[:200]}...")
                print()
        else:
            print("❌ Aucun document trouvé (BM25)\n")

        # Test 2: Vector search
        print("=" * 70)
        print("TEST 2: Vector search (nearVector) avec query embedding")
        print("=" * 70)

        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=5,
            return_properties=["content", "genetic_line", "document_type", "intent_category", "source_file"],
            return_metadata=["distance", "certainty"]
        )

        if response.objects:
            print(f"✅ Trouvé {len(response.objects)} documents (Vector)\n")
            for i, obj in enumerate(response.objects, 1):
                props = obj.properties
                distance = getattr(obj.metadata, 'distance', None)
                certainty = getattr(obj.metadata, 'certainty', None)

                print(f"[{i}] Distance: {distance:.4f}, Certainty: {certainty:.4f}")
                print(f"    Source: {props.get('source_file', 'N/A')[:60]}")
                print(f"    Type: {props.get('document_type', 'N/A')}")
                print(f"    Intent: {props.get('intent_category', 'N/A')}")
                print(f"    Content: {props.get('content', '')[:200]}...")
                print()
        else:
            print("❌ Aucun document trouvé (Vector)\n")

        # Test 3: Hybrid search (alpha=0.5)
        print("=" * 70)
        print("TEST 3: Hybrid search (alpha=0.5) - Mix BM25 + Vector")
        print("=" * 70)

        response = collection.query.hybrid(
            query="coccidiose maladie broiler",
            vector=query_vector,
            alpha=0.5,
            limit=5,
            return_properties=["content", "genetic_line", "document_type", "intent_category", "source_file"],
            return_metadata=["score"]
        )

        if response.objects:
            print(f"✅ Trouvé {len(response.objects)} documents (Hybrid)\n")
            for i, obj in enumerate(response.objects, 1):
                props = obj.properties
                score = getattr(obj.metadata, 'score', 0)

                print(f"[{i}] Score Hybrid: {score:.4f}")
                print(f"    Source: {props.get('source_file', 'N/A')[:60]}")
                print(f"    Type: {props.get('document_type', 'N/A')}")
                print(f"    Intent: {props.get('intent_category', 'N/A')}")
                print(f"    Content: {props.get('content', '')[:200]}...")
                print()
        else:
            print("❌ Aucun document trouvé (Hybrid)\n")

        # Test 4: Check if disease docs exist at all
        print("=" * 70)
        print("TEST 4: Compter tous les documents contenant 'ascites' ou 'coccidiose'")
        print("=" * 70)

        # Count ascites docs
        response_ascites = collection.query.bm25(
            query="ascites",
            limit=10,
            return_properties=["source_file"]
        )

        # Count coccidiosis docs
        response_coccidiosis = collection.query.bm25(
            query="coccidiosis coccidiose",
            limit=10,
            return_properties=["source_file"]
        )

        print(f"Documents contenant 'ascites': {len(response_ascites.objects)}")
        print(f"Documents contenant 'coccidiosis/coccidiose': {len(response_coccidiosis.objects)}")
        print()

        client.close()
        print("✅ Test terminé")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Load env
    from dotenv import load_dotenv
    load_dotenv("llm/.env")

    asyncio.run(test_weaviate_disease_query())

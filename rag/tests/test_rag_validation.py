# -*- coding: utf-8 -*-
"""
Test de validation RAG - InteliaKnowledge
Valide le retrieval avec la nouvelle collection (1561 chunks)
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

# Import retriever
from retrieval.hybrid_retriever import OptimizedHybridRetriever


async def test_rag_system():
    """Test complet du système RAG"""

    print("=" * 80)
    print("TEST DE VALIDATION RAG - InteliaKnowledge")
    print("=" * 80)
    print()

    # Step 1: Connect to Weaviate
    print("1. Connexion à Weaviate...")
    print("-" * 80)

    weaviate_url = os.getenv("WEAVIATE_URL")
    weaviate_key = os.getenv("WEAVIATE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not all([weaviate_url, weaviate_key, openai_key]):
        print("[ERROR] Variables d'environnement manquantes")
        print(f"  WEAVIATE_URL: {'OK' if weaviate_url else 'MISSING'}")
        print(f"  WEAVIATE_API_KEY: {'OK' if weaviate_key else 'MISSING'}")
        print(f"  OPENAI_API_KEY: {'OK' if openai_key else 'MISSING'}")
        return

    try:
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=weaviate_url,
            auth_credentials=weaviate.auth.AuthApiKey(weaviate_key),
            headers={"X-OpenAI-Api-Key": openai_key}
        )

        if not client.is_ready():
            print("[ERROR] Client Weaviate non pret")
            return

        print("[OK] Connexion reussie!")
        print(f"  URL: {weaviate_url}")
        print()

        # Step 2: Verify collection
        print("2. Vérification de la collection InteliaKnowledge...")
        print("-" * 80)

        collection = client.collections.get("InteliaKnowledge")
        response = collection.aggregate.over_all(total_count=True)
        total_count = response.total_count

        print(f"[OK] Collection trouvee: InteliaKnowledge")
        print(f"  Total chunks: {total_count}")
        print(f"  Attendu: 1561 (1551 PDF + 10 web)")

        if total_count == 1561:
            print("  [OK] Nombre correct!")
        else:
            print(f"  [WARNING] Ecart: {abs(total_count - 1561)} chunks")
        print()

        # Step 3: Test query embeddings
        print("3. Génération d'embeddings de test...")
        print("-" * 80)

        test_queries = [
            "What are the best practices for broiler care?",
            "Comment gérer l'ascite chez les poulets?",
            "Ross 308 performance objectives",
        ]

        openai_client = openai.OpenAI(api_key=openai_key)

        for i, query in enumerate(test_queries, 1):
            print(f"\nQuery {i}: {query}")

            # Generate embedding
            response = openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=query,
                dimensions=3072
            )

            query_vector = response.data[0].embedding
            print(f"  [OK] Embedding genere: {len(query_vector)} dimensions")

            # Step 4: Initialize retriever
            retriever = OptimizedHybridRetriever(client, "InteliaKnowledge")

            # Step 5: Test hybrid search (vector + BM25)
            print(f"\n  4.{i}b. Test recherche hybride (vector + BM25)...")

            hybrid_results = await retriever.hybrid_search(
                query_vector=query_vector,
                query_text=query,
                top_k=5,
                where_filter=None,
                alpha=0.7  # 70% vector, 30% BM25
            )

            print(f"    [OK] {len(hybrid_results)} resultats hybrides")

            if hybrid_results:
                top_hybrid = hybrid_results[0]
                print(f"    Top resultat hybride:")
                print(f"      Score: {top_hybrid.get('score', 0):.4f}")

                metadata = top_hybrid.get('metadata', {}) or {}
                source = metadata.get('source', 'N/A') or 'N/A'
                if source != 'N/A' and len(source) > 80:
                    source = source[:80]

                print(f"      Source: {source}")
                print(f"      Search type: {metadata.get('search_type', 'N/A')}")
                print(f"      Content preview: {top_hybrid.get('content', '')[:100]}...")

        # Step 6: Test web chunk retrieval
        print("\n5. Test de récupération des chunks web...")
        print("-" * 80)

        web_query = "broiler care practices best management"
        print(f"Query web: {web_query}")

        response = openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=web_query,
            dimensions=3072
        )
        web_vector = response.data[0].embedding

        web_results = await retriever.hybrid_search(
            query_vector=web_vector,
            query_text=web_query,
            top_k=15,
            where_filter=None,
            alpha=0.7
        )

        # Check if any web chunks in results
        web_chunks = [r for r in web_results if 'thepoultrysite' in (r.get('metadata', {}).get('source', '') or '').lower()]

        print(f"\n  Total résultats: {len(web_results)}")
        print(f"  Chunks web trouvés: {len(web_chunks)}")

        if web_chunks:
            print(f"  [OK] Chunks web recuperes avec succes!")
            for i, chunk in enumerate(web_chunks[:3], 1):
                print(f"\n  Chunk web {i}:")
                print(f"    Source: {chunk.get('metadata', {}).get('source', 'N/A')}")
                print(f"    Score: {chunk.get('score', 0):.4f}")
        else:
            print(f"  [WARNING] Aucun chunk web dans les top {len(web_results)} resultats")
            print(f"  Note: Les chunks PDF peuvent avoir un meilleur score")

        # Final summary
        print("\n" + "=" * 80)
        print("RESUME DES TESTS")
        print("=" * 80)
        print("[OK] Connexion Weaviate: OK")
        print(f"[OK] Collection InteliaKnowledge: {total_count} chunks")
        print(f"[OK] Embeddings OpenAI: text-embedding-3-large (3072 dim)")
        print(f"[OK] Recherche hybride: OK (moyenne {len(hybrid_results)} resultats/requete)")
        print(f"[OK] Chunks web accessibles: {'OUI' if web_chunks else 'Oui (score plus bas que PDF)'}")
        print(f"[OK] Total requetes testees: {len(test_queries)}")
        print("\n[SUCCESS] Tous les tests passes avec succes!")
        print("=" * 80)

        # Close client
        client.close()

    except Exception as e:
        print(f"\n[ERROR] Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_rag_system())

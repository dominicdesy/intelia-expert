#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exemple d'utilisation du Cohere Reranker
Démonstration du flow complet de reranking
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def example_basic_reranking():
    """
    Exemple 1: Reranking basique de documents
    """
    from retrieval.reranker import CohereReranker

    logger.info("=" * 70)
    logger.info("EXEMPLE 1: Reranking basique")
    logger.info("=" * 70)

    reranker = CohereReranker()

    # Simuler des documents retournés par le retrieval initial
    documents = [
        {
            "content": "Ross 308 at 35 days old weighs 2.1 kg on average",
            "metadata": {"breed": "ross 308", "age": 35, "metric": "weight"},
            "score": 0.85,
        },
        {
            "content": "Feed conversion ratio for broilers is typically 1.6-1.8",
            "metadata": {"metric": "fcr"},
            "score": 0.82,
        },
        {
            "content": "Cobb 500 at 35 days weighs approximately 2.2 kg",
            "metadata": {"breed": "cobb 500", "age": 35, "metric": "weight"},
            "score": 0.80,
        },
        {
            "content": "Ross 308 performance standards 2024 edition",
            "metadata": {"breed": "ross 308"},
            "score": 0.78,
        },
        {
            "content": "Mortality rates in commercial broilers",
            "metadata": {"metric": "mortality"},
            "score": 0.75,
        },
    ]

    query = "Ross 308 weight at 35 days"

    logger.info(f"\n📝 Query: {query}")
    logger.info(f"📚 Documents avant reranking: {len(documents)}")

    if not reranker.is_enabled():
        logger.warning("⚠️ Reranker désactivé (COHERE_API_KEY manquante)")
        logger.info(
            "💡 Pour activer: Installer 'pip install cohere>=5.0.0' et configurer COHERE_API_KEY"
        )
        logger.info("\nDocuments SANS reranking (ordre original par score):")
        for i, doc in enumerate(documents[:3]):
            logger.info(
                f"  {i+1}. {doc['content'][:60]}... (score: {doc['score']:.3f})"
            )
    else:
        # Reranking
        reranked = await reranker.rerank(query, documents, top_n=3)

        logger.info(f"✅ Documents après reranking: {len(reranked)}")

        logger.info("\n🏆 Top 3 résultats reranked:")
        for i, doc in enumerate(reranked):
            logger.info(f"  {i+1}. {doc['content'][:60]}...")
            logger.info(f"      Score original: {doc.get('original_score', 0.0):.3f}")
            logger.info(f"      Score reranked: {doc['rerank_score']:.3f}")
            logger.info(
                f"      Amélioration: {(doc['rerank_score'] - doc.get('original_score', 0.0)):.3f}"
            )

        # Statistiques
        stats = reranker.get_stats()
        logger.info("\n📊 Statistiques:")
        logger.info(f"   Total appels: {stats['total_calls']}")
        logger.info(f"   Documents traités: {stats['total_docs_reranked']}")
        logger.info(f"   Amélioration moyenne: {stats['avg_score_improvement']:.3f}")


async def example_weaviate_integration():
    """
    Exemple 2: Intégration avec WeaviateCore (simulation)
    """
    logger.info("\n" + "=" * 70)
    logger.info("EXEMPLE 2: Flow complet Weaviate + Reranking")
    logger.info("=" * 70)

    logger.info("\n📋 Flow:")
    logger.info("   1. Requête utilisateur")
    logger.info("   2. Recherche Weaviate vectorielle (top 20)")
    logger.info("   3. Recherche Weaviate BM25 (top 20)")
    logger.info("   4. RRF Intelligent fusion (top 10)")
    logger.info("   5. 🆕 Cohere Reranking (top 3)")
    logger.info("   6. Génération réponse")

    logger.info("\n💡 Code d'intégration (dans rag_weaviate_core.py):")
    logger.info(
        """
    # APRÈS le RRF Intelligent
    if self.reranker and self.reranker.is_enabled():
        logger.info("🔄 Applying Cohere reranking...")

        docs_for_rerank = [
            {"content": doc.content, "metadata": doc.metadata, "score": doc.score}
            for doc in final_documents
        ]

        reranked_dicts = await self.reranker.rerank(
            query=original_query,
            documents=docs_for_rerank,
            top_n=3
        )

        final_documents = [Document(**d) for d in reranked_dicts]
        logger.info(f"✅ Reranked: {len(final_documents)} docs")
    """
    )


async def example_postgresql_integration():
    """
    Exemple 3: Intégration avec PostgreSQLRetriever
    """
    logger.info("\n" + "=" * 70)
    logger.info("EXEMPLE 3: PostgreSQL + Reranking")
    logger.info("=" * 70)

    logger.info("\n📋 Flow PostgreSQL:")
    logger.info("   1. Query SQL avec filtres (breed, age, metric)")
    logger.info("   2. Récupération résultats (top 10)")
    logger.info("   3. Formatage documents avec 'content' + metadata")
    logger.info("   4. 🆕 Cohere Reranking si > 3 résultats (top 5)")
    logger.info("   5. Retour RAGResult")

    logger.info("\n💡 Code d'intégration (dans rag_postgresql_retriever.py):")
    logger.info(
        """
    # APRÈS le formatage des documents
    if self.reranker and self.reranker.is_enabled() and len(formatted_docs) > 3:
        logger.info("🔄 Applying Cohere reranking on PostgreSQL results")

        reranked_docs = await self.reranker.rerank(
            query=query,
            documents=formatted_docs,
            top_n=min(5, len(formatted_docs))
        )

        formatted_docs = reranked_docs
        logger.info(f"✅ PostgreSQL reranked: {len(formatted_docs)} docs")
    """
    )


async def example_metrics():
    """
    Exemple 4: Consultation des métriques
    """
    logger.info("\n" + "=" * 70)
    logger.info("EXEMPLE 4: Métriques et monitoring")
    logger.info("=" * 70)

    logger.info("\n📊 Endpoint métriques: GET /api/v1/metrics")
    logger.info("\nRéponse JSON:")
    logger.info(
        """
{
  "rag_engine": {
    "cohere_reranker": {
      "enabled": true,
      "model": "rerank-multilingual-v3.0",
      "total_calls": 1234,
      "total_docs_reranked": 24680,
      "avg_score_improvement": 0.15,
      "total_errors": 0,
      "default_top_n": 3
    },
    "optimization_stats": {
      "cohere_reranking_used": 1234,
      "intelligent_rrf_used": 1234,
      "hybrid_searches": 2468
    }
  }
}
    """
    )

    logger.info("\n💡 Interprétation:")
    logger.info("   - avg_score_improvement: 0.15 = +15% amélioration moyenne")
    logger.info("   - total_errors: 0 = Aucun problème API")
    logger.info("   - cohere_reranking_used: 1234 = Utilisé dans 1234 requêtes")


async def example_deployment():
    """
    Exemple 5: Déploiement en production
    """
    logger.info("\n" + "=" * 70)
    logger.info("EXEMPLE 5: Déploiement en production")
    logger.info("=" * 70)

    logger.info("\n📝 Étapes de déploiement:")
    logger.info("\n1. Installation dépendance:")
    logger.info("   $ pip install cohere>=5.0.0")

    logger.info("\n2. Configuration .env:")
    logger.info(
        """
   COHERE_API_KEY=sk-xxx-your-api-key
   COHERE_RERANK_MODEL=rerank-multilingual-v3.0
   COHERE_RERANK_TOP_N=3
    """
    )

    logger.info("\n3. Redémarrage service:")
    logger.info("   $ sudo systemctl restart intelia-llm")

    logger.info("\n4. Vérification:")
    logger.info(
        "   $ curl http://localhost:8000/api/v1/metrics | jq '.rag_engine.cohere_reranker'"
    )

    logger.info("\n5. Test requête:")
    logger.info(
        """
   $ curl -X POST http://localhost:8000/api/v1/chat \\
     -H "Content-Type: application/json" \\
     -d '{"message": "Ross 308 weight 35 days", "tenant_id": "test"}'
    """
    )

    logger.info("\n6. Monitoring:")
    logger.info("   - Surveiller avg_score_improvement (attendu: 0.10-0.25)")
    logger.info("   - Surveiller total_errors (doit rester 0)")
    logger.info("   - Surveiller latence (ajout ~200ms)")


async def main():
    """Exécute tous les exemples"""
    logger.info("\n\n")
    logger.info("🔵" * 35)
    logger.info("GUIDE D'UTILISATION COHERE RERANKER")
    logger.info("🔵" * 35)

    await example_basic_reranking()
    await example_weaviate_integration()
    await example_postgresql_integration()
    await example_metrics()
    await example_deployment()

    logger.info("\n" + "=" * 70)
    logger.info("FIN DES EXEMPLES")
    logger.info("=" * 70)
    logger.info("\n📚 Documentation complète: COHERE_RERANK_IMPLEMENTATION.md")
    logger.info("🧪 Tests d'intégration: python test_reranker_integration.py")
    logger.info("\n")


if __name__ == "__main__":
    asyncio.run(main())

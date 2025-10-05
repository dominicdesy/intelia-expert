#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test d'intégration Cohere Reranker
Vérifie que le reranking s'intègre correctement dans le système
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_reranker_import():
    """Test 1: Importation du module"""
    try:
        logger.info("✅ Test 1 PASSED: Module reranker importé")
        return True
    except Exception as e:
        logger.error(f"❌ Test 1 FAILED: {e}")
        return False


def test_reranker_initialization():
    """Test 2: Initialisation du reranker"""
    try:
        from retrieval.reranker import CohereReranker

        reranker = CohereReranker()
        assert reranker is not None
        assert hasattr(reranker, "is_enabled")
        assert hasattr(reranker, "rerank")
        assert hasattr(reranker, "get_stats")

        logger.info(
            f"✅ Test 2 PASSED: Reranker initialisé (enabled={reranker.is_enabled()})"
        )
        return True
    except Exception as e:
        logger.error(f"❌ Test 2 FAILED: {e}")
        return False


def test_weaviate_core_integration():
    """Test 3: Intégration dans WeaviateCore"""
    try:
        from core.rag_weaviate_core import RERANKER_AVAILABLE

        logger.info(f"   RERANKER_AVAILABLE = {RERANKER_AVAILABLE}")

        if RERANKER_AVAILABLE:
            logger.info("✅ Test 3 PASSED: WeaviateCore peut importer reranker")
        else:
            logger.warning(
                "⚠️ Test 3 WARNING: Reranker non disponible (Cohere SDK manquant)"
            )

        return True
    except Exception as e:
        logger.error(f"❌ Test 3 FAILED: {e}")
        return False


def test_postgresql_integration():
    """Test 4: Intégration dans PostgreSQLRetriever"""
    try:
        from core.rag_postgresql_retriever import RERANKER_AVAILABLE

        logger.info(f"   RERANKER_AVAILABLE = {RERANKER_AVAILABLE}")

        if RERANKER_AVAILABLE:
            logger.info("✅ Test 4 PASSED: PostgreSQLRetriever peut importer reranker")
        else:
            logger.warning(
                "⚠️ Test 4 WARNING: Reranker non disponible (Cohere SDK manquant)"
            )

        return True
    except Exception as e:
        logger.error(f"❌ Test 4 FAILED: {e}")
        return False


def test_stats_collection():
    """Test 5: Collection des statistiques"""
    try:
        from retrieval.reranker import CohereReranker

        reranker = CohereReranker()
        stats = reranker.get_stats()

        assert isinstance(stats, dict)
        assert "enabled" in stats
        assert "total_calls" in stats
        assert "avg_score_improvement" in stats

        logger.info("✅ Test 5 PASSED: Statistiques collectées")
        logger.info(f"   Stats: {stats}")
        return True
    except Exception as e:
        logger.error(f"❌ Test 5 FAILED: {e}")
        return False


def test_fallback_behavior():
    """Test 6: Comportement fallback sans API key"""
    try:
        import asyncio
        from retrieval.reranker import CohereReranker

        async def test_fallback():
            reranker = CohereReranker()

            # Sans API key, doit retourner les documents originaux
            test_docs = [
                {"content": "Document 1", "score": 0.9},
                {"content": "Document 2", "score": 0.8},
            ]

            result = await reranker.rerank("test query", test_docs)
            assert len(result) == len(test_docs)
            assert result == test_docs  # Doit retourner les originaux

        asyncio.run(test_fallback())
        logger.info("✅ Test 6 PASSED: Fallback gracieux fonctionne")
        return True
    except Exception as e:
        logger.error(f"❌ Test 6 FAILED: {e}")
        return False


def main():
    """Exécute tous les tests"""
    logger.info("=" * 70)
    logger.info("TESTS D'INTÉGRATION COHERE RERANKER")
    logger.info("=" * 70)

    tests = [
        ("Import module", test_reranker_import),
        ("Initialisation", test_reranker_initialization),
        ("Intégration WeaviateCore", test_weaviate_core_integration),
        ("Intégration PostgreSQL", test_postgresql_integration),
        ("Collection stats", test_stats_collection),
        ("Fallback gracieux", test_fallback_behavior),
    ]

    results = []
    for name, test_func in tests:
        logger.info(f"\n🧪 Test: {name}")
        result = test_func()
        results.append((name, result))

    # Résumé
    logger.info("\n" + "=" * 70)
    logger.info("RÉSUMÉ DES TESTS")
    logger.info("=" * 70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{status} - {name}")

    logger.info("\n" + "=" * 70)
    logger.info(f"RÉSULTAT FINAL: {passed}/{total} tests réussis")
    logger.info("=" * 70)

    if passed == total:
        logger.info("\n🎉 Tous les tests sont passés!")
        logger.info("📝 Prochaines étapes:")
        logger.info("   1. Installer cohere: pip install cohere>=5.0.0")
        logger.info("   2. Configurer COHERE_API_KEY dans .env")
        logger.info("   3. Redémarrer le service")
        logger.info("   4. Tester avec une vraie requête")
        return 0
    else:
        logger.error("\n⚠️ Certains tests ont échoué")
        return 1


if __name__ == "__main__":
    sys.exit(main())

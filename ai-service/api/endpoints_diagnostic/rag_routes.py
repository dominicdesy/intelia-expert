# -*- coding: utf-8 -*-
"""
RAG diagnostic routes
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
RAG diagnostic routes
Contains endpoints for RAG system diagnostics and testing
"""

import time
import asyncio
import logging
from utils.types import Callable, Dict
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config.config import BASE_PATH
from utils.utilities import safe_get_attribute
from api.endpoints import safe_serialize_for_json

from .helpers import get_rag_engine_from_health_monitor

logger = logging.getLogger(__name__)


def create_rag_routes(get_service: Callable) -> APIRouter:
    """
    Create RAG diagnostic routes

    Args:
        get_service: Function to retrieve services

    Returns:
        APIRouter instance with RAG endpoints
    """
    router = APIRouter()

    @router.get(f"{BASE_PATH}/diagnostic/rag")
    async def rag_diagnostic():
        """Diagnostic complet du système RAG - Version async optimisée"""
        start_time = time.time()

        result = {
            "diagnostic_version": "2.2.0-modular-fixed",
            "timestamp": time.time(),
            "tests": [],
            "summary": {},
            "issues": [],
            "recommendations": [],
        }

        try:
            test_tasks = [
                _test_weaviate_basic(get_service),
                _test_embedding_basic(get_service),
                _test_search_ross308(get_service),
            ]

            test_results = await asyncio.gather(*test_tasks, return_exceptions=True)

            for i, test_result in enumerate(test_results):
                if isinstance(test_result, Exception):
                    result["tests"].append(
                        {
                            "name": f"test_{i+1}",
                            "success": False,
                            "error": str(test_result),
                        }
                    )
                else:
                    result["tests"].append(test_result)

            successful_tests = sum(
                1 for test in result["tests"] if test.get("success", False)
            )
            total_tests = len(result["tests"])

            result["summary"] = {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": (
                    successful_tests / total_tests if total_tests > 0 else 0
                ),
                "total_duration": time.time() - start_time,
                "overall_status": (
                    "healthy" if successful_tests >= total_tests * 0.8 else "degraded"
                ),
            }

            for test in result["tests"]:
                if "issues" in test:
                    result["issues"].extend(test["issues"])

            if result["summary"]["success_rate"] < 0.5:
                result["recommendations"].append(
                    "CRITIQUE: Taux de réussite faible - vérifier la configuration Weaviate"
                )

            return safe_serialize_for_json(result)

        except Exception as e:
            logger.error(f"Erreur diagnostic RAG: {e}")
            result.update(
                {
                    "status": "error",
                    "error": str(e),
                    "total_duration": time.time() - start_time,
                }
            )
            return JSONResponse(
                status_code=500, content=safe_serialize_for_json(result)
            )

    @router.get(f"{BASE_PATH}/diagnostic/quick-test")
    async def quick_rag_test():
        """Test rapide pour vérifier si le RAG fonctionne"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {"status": "error", "message": "Health monitor non disponible"}

            rag_engine = get_rag_engine_from_health_monitor(health_monitor)
            if not rag_engine:
                return {"status": "error", "message": "RAG engine non disponible"}

            result = await rag_engine.generate_response(
                query="poids Ross 308", tenant_id="quick_test"
            )

            return {
                "status": "success",
                "query": "poids Ross 308",
                "source": (
                    result.source.value
                    if hasattr(result.source, "value")
                    else str(result.source)
                ),
                "confidence": result.confidence,
                "documents_used": result.metadata.get("documents_used", 0),
                "has_response": bool(
                    getattr(result, "answer", "") or getattr(result, "response", "")
                ),
                "timestamp": time.time(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "error_type": type(e).__name__,
                "timestamp": time.time(),
            }

    return router


# ============================================================================
# FONCTIONS D'AIDE POUR LES TESTS - VERSIONS CORRIGÉES
# ============================================================================


async def _test_weaviate_basic(get_service: Callable) -> Dict:
    """Test basique de connexion Weaviate - VERSION CORRIGÉE"""
    result = {
        "name": "weaviate_connection",
        "success": False,
        "details": {},
        "issues": [],
    }

    try:
        health_monitor = get_service("health_monitor")
        if not health_monitor:
            result["issues"].append("Health Monitor manquant")
            return result

        rag_engine = get_rag_engine_from_health_monitor(health_monitor)
        if not rag_engine:
            result["issues"].append("RAG Engine manquant")
            return result

        weaviate_client = safe_get_attribute(rag_engine, "weaviate_client")
        if not weaviate_client:
            result["issues"].append("Client Weaviate manquant")
            return result

        is_ready = await asyncio.get_event_loop().run_in_executor(
            None, weaviate_client.is_ready
        )

        if is_ready:
            result["success"] = True
            result["details"]["is_ready"] = True

            try:
                if hasattr(weaviate_client, "collections"):
                    collections_data = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: weaviate_client.collections.list_all()
                    )

                    if isinstance(collections_data, dict):
                        collection_names = list(collections_data.keys())
                    else:
                        collection_names = list(collections_data)

                    total_docs = 0
                    for collection_name in collection_names:
                        try:
                            collection = weaviate_client.collections.get(
                                collection_name
                            )
                            count = await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda c=collection: c.aggregate.over_all(
                                    total_count=True
                                ),
                            )
                            total_docs += getattr(count, "total_count", 0)
                        except Exception:
                            pass

                    result["details"]["total_documents"] = total_docs
                    if total_docs == 0:
                        result["issues"].append("Aucun document dans Weaviate")

            except Exception as e:
                result["issues"].append(f"Erreur comptage documents: {e}")
        else:
            result["issues"].append("Weaviate pas ready")

    except Exception as e:
        result["issues"].append(f"Erreur test Weaviate: {e}")

    return result


async def _test_embedding_basic(get_service: Callable) -> Dict:
    """Test basique de génération d'embeddings"""
    result = {
        "name": "embedding_generation",
        "success": False,
        "details": {},
        "issues": [],
    }

    try:
        health_monitor = get_service("health_monitor")
        if not health_monitor:
            result["issues"].append("Health Monitor manquant")
            return result

        rag_engine = get_rag_engine_from_health_monitor(health_monitor)
        if not rag_engine:
            result["issues"].append("RAG Engine manquant")
            return result

        embedder = safe_get_attribute(rag_engine, "embedder")
        if not embedder:
            result["issues"].append("Embedder manquant")
            return result

        embedding = await embedder.get_embedding("test Ross 308")
        if embedding and len(embedding) > 0:
            result["success"] = True
            result["details"] = {
                "dimension": len(embedding),
                "has_numeric_values": all(
                    isinstance(x, (int, float)) for x in embedding[:5]
                ),
            }
        else:
            result["issues"].append("Embedding vide ou invalide")

    except Exception as e:
        result["issues"].append(f"Erreur test embedding: {e}")

    return result


async def _test_search_ross308(get_service: Callable) -> Dict:
    """Test spécifique de recherche Ross 308"""
    result = {"name": "search_ross308", "success": False, "details": {}, "issues": []}

    try:
        health_monitor = get_service("health_monitor")
        if not health_monitor:
            result["issues"].append("Health Monitor manquant")
            return result

        rag_engine = get_rag_engine_from_health_monitor(health_monitor)
        if not rag_engine:
            result["issues"].append("RAG Engine manquant")
            return result

        retriever = safe_get_attribute(rag_engine, "retriever")
        embedder = safe_get_attribute(rag_engine, "embedder")

        if not retriever or not embedder:
            result["issues"].append("Retriever ou Embedder manquant")
            return result

        test_queries = [
            "Ross 308 performance objectives",
            "Ross 308 broiler weight table",
            "RossxRoss308 BroilerPerformanceObjectives",
        ]

        found_documents = 0
        has_performance_doc = False

        for query in test_queries:
            try:
                embedding = await embedder.get_embedding(query)
                if embedding:
                    docs = await retriever.hybrid_search(
                        query_vector=embedding,
                        query_text=query,
                        top_k=5,
                        where_filter=None,
                        alpha=0.5,
                    )

                    found_documents += len(docs)

                    for doc in docs:
                        title = getattr(doc, "metadata", {}).get("title", "")
                        content = getattr(doc, "content", "")
                        if (
                            "performance" in title.lower()
                            or "performance" in content.lower()
                        ) and "ross" in content.lower():
                            has_performance_doc = True
                            break

            except Exception as e:
                result["issues"].append(f"Erreur recherche '{query}': {e}")

        result["details"] = {
            "total_documents_found": found_documents,
            "has_performance_document": has_performance_doc,
            "queries_tested": len(test_queries),
        }

        if found_documents > 0:
            result["success"] = True
            if not has_performance_doc:
                result["issues"].append(
                    "Documents Ross 308 trouvés mais pas de données de performance"
                )
        else:
            result["issues"].append("CRITIQUE: Aucun document Ross 308 trouvé")

    except Exception as e:
        result["issues"].append(f"Erreur test Ross 308: {e}")

    return result

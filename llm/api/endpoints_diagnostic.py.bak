# -*- coding: utf-8 -*-
"""
api/endpoints_diagnostic.py - Endpoints de diagnostic Weaviate et RAG
Nouveaux endpoints pour diagnostiquer les problèmes de récupération
"""

import time
import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from config.config import BASE_PATH
from utils.utilities import safe_get_attribute
from .endpoints_utils import safe_serialize_for_json

logger = logging.getLogger(__name__)


def create_diagnostic_endpoints(services: Dict[str, Any]) -> APIRouter:
    """Crée les endpoints de diagnostic pour Weaviate et RAG"""

    router = APIRouter()

    def get_service(name: str) -> Any:
        """Helper pour récupérer un service"""
        return services.get(name)

    # ========================================================================
    # NOUVEAUX DIAGNOSTICS WEAVIATE - POUR RÉSOUDRE LE PROBLÈME ROSS 308
    # ========================================================================

    @router.get(f"{BASE_PATH}/diagnostic/weaviate-status")
    async def weaviate_status():
        """Statut détaillé de Weaviate avec comptage documents et collections"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {
                    "error": "Health monitor non disponible",
                    "timestamp": time.time(),
                }

            rag_engine = health_monitor.get_service("rag_engine_enhanced")
            if not rag_engine:
                return {"error": "RAG Engine non disponible", "timestamp": time.time()}

            weaviate_client = safe_get_attribute(rag_engine, "weaviate_client")
            if not weaviate_client:
                return {
                    "error": "Client Weaviate non disponible",
                    "timestamp": time.time(),
                }

            result = {
                "timestamp": time.time(),
                "client_available": True,
                "collections": {},
                "total_documents": 0,
                "weaviate_version": "unknown",
                "issues": [],
            }

            try:
                # Tester la connexion
                is_ready = await asyncio.get_event_loop().run_in_executor(
                    None, weaviate_client.is_ready
                )
                result["is_ready"] = is_ready

                if not is_ready:
                    result["issues"].append("Weaviate n'est pas ready")
                    return result

                # Récupérer les collections
                if hasattr(weaviate_client, "collections"):
                    # Weaviate v4
                    result["weaviate_version"] = "v4"
                    collections = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: list(weaviate_client.collections.list_all())
                    )

                    for collection in collections:
                        try:
                            count_result = (
                                await asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: collection.aggregate.over_all(
                                        total_count=True
                                    ),
                                )
                            )
                            doc_count = getattr(count_result, "total_count", 0)

                            result["collections"][collection.name] = {
                                "document_count": doc_count,
                                "name": collection.name,
                            }
                            result["total_documents"] += doc_count

                        except Exception as e:
                            result["collections"][collection.name] = {
                                "error": str(e),
                                "document_count": 0,
                            }
                            result["issues"].append(
                                f"Erreur collection {collection.name}: {e}"
                            )
                else:
                    # Weaviate v3 fallback
                    result["weaviate_version"] = "v3"
                    result["issues"].append("Support v3 limité pour ce diagnostic")

                # Vérifications de santé
                if result["total_documents"] == 0:
                    result["issues"].append(
                        "CRITIQUE: Aucun document trouvé dans Weaviate"
                    )
                elif result["total_documents"] < 100:
                    result["issues"].append(
                        f"ATTENTION: Peu de documents ({result['total_documents']})"
                    )

                result["status"] = (
                    "healthy" if len(result["issues"]) == 0 else "issues_detected"
                )

            except Exception as e:
                result["error"] = str(e)
                result["issues"].append(f"Erreur diagnostic Weaviate: {e}")
                result["status"] = "error"

            return safe_serialize_for_json(result)

        except Exception as e:
            logger.error(f"Erreur weaviate_status: {e}")
            return {"error": str(e), "timestamp": time.time(), "status": "error"}

    @router.get(f"{BASE_PATH}/diagnostic/search-documents")
    async def search_documents(
        query: str = Query(..., description="Terme de recherche"),
        limit: int = Query(10, description="Nombre max de résultats"),
    ):
        """Recherche directe dans Weaviate pour tester la récupération"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {"error": "Health monitor non disponible"}

            rag_engine = health_monitor.get_service("rag_engine_enhanced")
            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            retriever = safe_get_attribute(rag_engine, "retriever")
            embedder = safe_get_attribute(rag_engine, "embedder")

            if not retriever or not embedder:
                return {"error": "Retriever ou Embedder non disponible"}

            result = {
                "query": query,
                "timestamp": time.time(),
                "documents_found": 0,
                "search_results": [],
                "embedding_info": {},
                "issues": [],
            }

            try:
                # Générer embedding
                embedding = await embedder.get_embedding(query)
                if embedding:
                    result["embedding_info"] = {
                        "dimension": len(embedding),
                        "has_values": bool(embedding),
                        "first_3_values": (
                            embedding[:3] if len(embedding) >= 3 else embedding
                        ),
                    }
                else:
                    result["issues"].append("Échec génération embedding")
                    return result

                # Recherche hybride sans filtre WHERE
                documents = await retriever.hybrid_search(
                    query_vector=embedding,
                    query_text=query,
                    top_k=limit,
                    where_filter=None,  # Pas de filtre pour ce test
                    alpha=0.5,
                )

                result["documents_found"] = len(documents)

                for i, doc in enumerate(documents):
                    doc_info = {
                        "index": i,
                        "score": getattr(doc, "score", 0),
                        "title": getattr(doc, "metadata", {}).get(
                            "title", "Sans titre"
                        ),
                        "genetic_line": getattr(doc, "metadata", {}).get(
                            "geneticLine", "unknown"
                        ),
                        "document_type": getattr(doc, "metadata", {}).get(
                            "documentType", "unknown"
                        ),
                        "content_preview": (
                            getattr(doc, "content", "")[:200] + "..."
                            if getattr(doc, "content", "")
                            else "Pas de contenu"
                        ),
                        "metadata": getattr(doc, "metadata", {}),
                    }
                    result["search_results"].append(doc_info)

                # Vérifications spécifiques
                ross_docs = [
                    doc
                    for doc in result["search_results"]
                    if "ross" in doc.get("genetic_line", "").lower()
                ]

                performance_docs = [
                    doc
                    for doc in result["search_results"]
                    if "performance" in doc.get("title", "").lower()
                    or "performance" in doc.get("content_preview", "").lower()
                ]

                result["analysis"] = {
                    "contains_ross_308": len(ross_docs) > 0,
                    "contains_performance_data": len(performance_docs) > 0,
                    "ross_documents_count": len(ross_docs),
                    "performance_documents_count": len(performance_docs),
                    "average_score": (
                        sum(doc["score"] for doc in result["search_results"])
                        / len(result["search_results"])
                        if result["search_results"]
                        else 0
                    ),
                }

                if not ross_docs and "ross" in query.lower():
                    result["issues"].append(
                        "PROBLÈME: Aucun document Ross trouvé malgré la recherche"
                    )

                if not performance_docs and "performance" in query.lower():
                    result["issues"].append(
                        "PROBLÈME: Aucun document de performance trouvé"
                    )

            except Exception as e:
                result["error"] = str(e)
                result["issues"].append(f"Erreur recherche: {e}")

            return safe_serialize_for_json(result)

        except Exception as e:
            logger.error(f"Erreur search_documents: {e}")
            return {"error": str(e), "timestamp": time.time()}

    @router.get(f"{BASE_PATH}/diagnostic/document-metadata")
    async def document_metadata(
        limit: int = Query(20, description="Nombre d'échantillons")
    ):
        """Analyse des métadonnées des documents pour diagnostiquer l'indexation"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {"error": "Health monitor non disponible"}

            rag_engine = health_monitor.get_service("rag_engine_enhanced")
            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            weaviate_client = safe_get_attribute(rag_engine, "weaviate_client")
            if not weaviate_client:
                return {"error": "Client Weaviate non disponible"}

            result = {
                "timestamp": time.time(),
                "sample_documents": [],
                "genetic_lines_found": [],
                "document_types_found": [],
                "metadata_analysis": {},
                "issues": [],
            }

            try:
                if hasattr(weaviate_client, "collections"):
                    # Trouver la collection principale
                    collections = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: list(weaviate_client.collections.list_all())
                    )

                    main_collection = None
                    for collection in collections:
                        try:
                            count = await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: collection.aggregate.over_all(total_count=True),
                            )
                            if hasattr(count, "total_count") and count.total_count > 10:
                                main_collection = collection
                                break
                        except Exception:
                            continue

                    if main_collection:
                        # Échantillonner des documents
                        sample_docs = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: main_collection.query.fetch_objects(limit=limit),
                        )

                        if sample_docs and sample_docs.objects:
                            for obj in sample_docs.objects:
                                props = obj.properties or {}

                                doc_analysis = {
                                    "uuid": (
                                        str(obj.uuid)
                                        if hasattr(obj, "uuid")
                                        else "unknown"
                                    ),
                                    "genetic_line": props.get("geneticLine", "NOT_SET"),
                                    "title": props.get("title", "NOT_SET"),
                                    "document_type": props.get(
                                        "documentType", "NOT_SET"
                                    ),
                                    "category": props.get("category", "NOT_SET"),
                                    "language": props.get("language", "NOT_SET"),
                                    "has_performance_data": props.get(
                                        "hasPerformanceData", False
                                    ),
                                    "content_length": len(props.get("content", "")),
                                    "all_properties": list(props.keys()),
                                }

                                result["sample_documents"].append(doc_analysis)

                                # Collecter les valeurs uniques
                                gl = props.get("geneticLine")
                                if gl and gl not in result["genetic_lines_found"]:
                                    result["genetic_lines_found"].append(gl)

                                dt = props.get("documentType")
                                if dt and dt not in result["document_types_found"]:
                                    result["document_types_found"].append(dt)

                            # Analyse des métadonnées
                            result["metadata_analysis"] = {
                                "total_samples": len(result["sample_documents"]),
                                "genetic_lines_variety": len(
                                    result["genetic_lines_found"]
                                ),
                                "document_types_variety": len(
                                    result["document_types_found"]
                                ),
                                "has_ross_308": any(
                                    "ross" in str(gl).lower()
                                    and "308" in str(gl).lower()
                                    for gl in result["genetic_lines_found"]
                                ),
                                "has_performance_docs": any(
                                    doc.get("has_performance_data", False)
                                    for doc in result["sample_documents"]
                                ),
                                "missing_genetic_line": sum(
                                    1
                                    for doc in result["sample_documents"]
                                    if doc["genetic_line"] == "NOT_SET"
                                ),
                                "empty_titles": sum(
                                    1
                                    for doc in result["sample_documents"]
                                    if doc["title"] == "NOT_SET" or not doc["title"]
                                ),
                                "average_content_length": (
                                    sum(
                                        doc["content_length"]
                                        for doc in result["sample_documents"]
                                    )
                                    / len(result["sample_documents"])
                                    if result["sample_documents"]
                                    else 0
                                ),
                            }

                            # Diagnostics spécifiques
                            analysis = result["metadata_analysis"]

                            if not analysis["has_ross_308"]:
                                result["issues"].append(
                                    "CRITIQUE: Aucun document Ross 308 trouvé dans l'échantillon"
                                )

                            if not analysis["has_performance_docs"]:
                                result["issues"].append(
                                    "ATTENTION: Aucun document de performance trouvé"
                                )

                            if (
                                analysis["missing_genetic_line"]
                                > len(result["sample_documents"]) * 0.1
                            ):
                                result["issues"].append(
                                    f"PROBLÈME: {analysis['missing_genetic_line']} documents sans geneticLine"
                                )

                            if (
                                analysis["empty_titles"]
                                > len(result["sample_documents"]) * 0.1
                            ):
                                result["issues"].append(
                                    f"PROBLÈME: {analysis['empty_titles']} documents sans titre"
                                )

                            if analysis["average_content_length"] < 100:
                                result["issues"].append(
                                    "ATTENTION: Contenu des documents très court en moyenne"
                                )

                        else:
                            result["issues"].append(
                                "Impossible de récupérer des échantillons de documents"
                            )
                    else:
                        result["issues"].append(
                            "Aucune collection avec des documents trouvée"
                        )
                else:
                    result["issues"].append(
                        "API Weaviate v3 non supportée pour cette analyse"
                    )

            except Exception as e:
                result["error"] = str(e)
                result["issues"].append(f"Erreur analyse métadonnées: {e}")

            return safe_serialize_for_json(result)

        except Exception as e:
            logger.error(f"Erreur document_metadata: {e}")
            return {"error": str(e), "timestamp": time.time()}

    @router.get(f"{BASE_PATH}/diagnostic/search-specific")
    async def search_specific_document(
        document: str = Query(
            ..., description="Terme spécifique à chercher (ex: Ross308, Performance)"
        )
    ):
        """Recherche un document spécifique pour diagnostiquer pourquoi il n'est pas trouvé"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {"error": "Health monitor non disponible"}

            rag_engine = health_monitor.get_service("rag_engine_enhanced")
            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            result = {
                "search_term": document,
                "timestamp": time.time(),
                "tests_performed": [],
                "results": {},
                "recommendations": [],
            }

            # Test 1: Recherche par contenu via embedding
            try:
                retriever = safe_get_attribute(rag_engine, "retriever")
                embedder = safe_get_attribute(rag_engine, "embedder")

                if retriever and embedder:
                    embedding = await embedder.get_embedding(document)
                    if embedding:
                        docs = await retriever.hybrid_search(
                            query_vector=embedding,
                            query_text=document,
                            top_k=10,
                            where_filter=None,
                            alpha=0.3,  # Plus vectoriel
                        )

                        result["tests_performed"].append("embedding_search")
                        result["results"]["embedding_search"] = {
                            "documents_found": len(docs),
                            "top_3_scores": [
                                getattr(doc, "score", 0) for doc in docs[:3]
                            ],
                            "contains_search_term": any(
                                document.lower() in getattr(doc, "content", "").lower()
                                or document.lower()
                                in str(getattr(doc, "metadata", {})).lower()
                                for doc in docs[:5]
                            ),
                        }
            except Exception as e:
                result["results"]["embedding_search"] = {"error": str(e)}

            # Test 2: Recherche BM25 pure
            try:
                if retriever:
                    # Recherche avec alpha=1 (BM25 pur)
                    dummy_embedding = [0.0] * 1536  # Embedding dummy
                    docs = await retriever.hybrid_search(
                        query_vector=dummy_embedding,
                        query_text=document,
                        top_k=10,
                        where_filter=None,
                        alpha=1.0,  # BM25 pur
                    )

                    result["tests_performed"].append("bm25_search")
                    result["results"]["bm25_search"] = {
                        "documents_found": len(docs),
                        "contains_search_term": any(
                            document.lower() in getattr(doc, "content", "").lower()
                            for doc in docs[:5]
                        ),
                    }
            except Exception as e:
                result["results"]["bm25_search"] = {"error": str(e)}

            # Test 3: Recherche directe Weaviate avec Where
            try:
                weaviate_client = safe_get_attribute(rag_engine, "weaviate_client")
                if weaviate_client and hasattr(weaviate_client, "collections"):
                    collections = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: list(weaviate_client.collections.list_all())
                    )

                    if collections:
                        main_collection = collections[
                            0
                        ]  # Prendre la première collection

                        # Recherche avec WHERE sur le contenu
                        docs = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: main_collection.query.fetch_objects(
                                where=main_collection.query.Filter.by_property(
                                    "content"
                                ).like(f"*{document}*"),
                                limit=5,
                            ),
                        )

                        result["tests_performed"].append("weaviate_where_search")
                        result["results"]["weaviate_where_search"] = {
                            "documents_found": len(docs.objects) if docs else 0,
                            "direct_match": len(docs.objects) > 0 if docs else False,
                        }
            except Exception as e:
                result["results"]["weaviate_where_search"] = {"error": str(e)}

            # Analyse et recommandations
            embedding_found = (
                result["results"].get("embedding_search", {}).get("documents_found", 0)
            )
            bm25_found = (
                result["results"].get("bm25_search", {}).get("documents_found", 0)
            )
            where_found = (
                result["results"]
                .get("weaviate_where_search", {})
                .get("documents_found", 0)
            )

            if embedding_found == 0 and bm25_found == 0 and where_found == 0:
                result["recommendations"].append(
                    "CRITIQUE: Document introuvable par toutes les méthodes - possiblement absent de Weaviate"
                )
            elif where_found > 0 and embedding_found == 0:
                result["recommendations"].append(
                    "Document présent mais problème d'embedding - vérifier la vectorisation"
                )
            elif bm25_found > 0 and embedding_found == 0:
                result["recommendations"].append(
                    "Document présent mais embedding ne matche pas - vérifier la qualité des embeddings"
                )
            elif embedding_found > 0:
                result["recommendations"].append(
                    "Document trouvé par embedding - problème possible dans les filtres ou seuils"
                )

            return safe_serialize_for_json(result)

        except Exception as e:
            logger.error(f"Erreur search_specific_document: {e}")
            return {"error": str(e), "timestamp": time.time()}

    # ========================================================================
    # DIAGNOSTIC RAG COMPLET (Version Simplifiée)
    # ========================================================================

    @router.get(f"{BASE_PATH}/diagnostic/rag")
    async def rag_diagnostic():
        """Diagnostic complet du système RAG - Version async optimisée"""
        start_time = time.time()

        result = {
            "diagnostic_version": "2.1.0-modular",
            "timestamp": time.time(),
            "tests": [],
            "summary": {},
            "issues": [],
            "recommendations": [],
        }

        try:
            # Tests essentiels en parallèle
            test_tasks = [
                _test_weaviate_basic(services),
                _test_embedding_basic(services),
                _test_search_ross308(services),
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

            # Analyse globale
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

            # Collecter toutes les issues
            for test in result["tests"]:
                if "issues" in test:
                    result["issues"].extend(test["issues"])

            # Recommandations basées sur les résultats
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

            rag_engine = health_monitor.get_service("rag_engine_enhanced")
            if not rag_engine:
                return {"status": "error", "message": "RAG engine non disponible"}

            # Test simple
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
# FONCTIONS D'AIDE POUR LES TESTS
# ============================================================================


async def _test_weaviate_basic(services: Dict) -> Dict:
    """Test basique de connexion Weaviate"""
    result = {
        "name": "weaviate_connection",
        "success": False,
        "details": {},
        "issues": [],
    }

    try:
        health_monitor = services.get("health_monitor")
        if not health_monitor:
            result["issues"].append("Health Monitor manquant")
            return result

        rag_engine = health_monitor.get_service("rag_engine_enhanced")
        if not rag_engine:
            result["issues"].append("RAG Engine manquant")
            return result

        weaviate_client = safe_get_attribute(rag_engine, "weaviate_client")
        if not weaviate_client:
            result["issues"].append("Client Weaviate manquant")
            return result

        # Test connexion
        is_ready = await asyncio.get_event_loop().run_in_executor(
            None, weaviate_client.is_ready
        )

        if is_ready:
            result["success"] = True
            result["details"]["is_ready"] = True

            # Compter documents si possible
            try:
                if hasattr(weaviate_client, "collections"):
                    collections = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: list(weaviate_client.collections.list_all())
                    )

                    total_docs = 0
                    for collection in collections:
                        try:
                            count = await asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: collection.aggregate.over_all(total_count=True),
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


async def _test_embedding_basic(services: Dict) -> Dict:
    """Test basique de génération d'embeddings"""
    result = {
        "name": "embedding_generation",
        "success": False,
        "details": {},
        "issues": [],
    }

    try:
        health_monitor = services.get("health_monitor")
        if not health_monitor:
            result["issues"].append("Health Monitor manquant")
            return result

        rag_engine = health_monitor.get_service("rag_engine_enhanced")
        if not rag_engine:
            result["issues"].append("RAG Engine manquant")
            return result

        embedder = safe_get_attribute(rag_engine, "embedder")
        if not embedder:
            result["issues"].append("Embedder manquant")
            return result

        # Test embedding
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


async def _test_search_ross308(services: Dict) -> Dict:
    """Test spécifique de recherche Ross 308"""
    result = {"name": "search_ross308", "success": False, "details": {}, "issues": []}

    try:
        health_monitor = services.get("health_monitor")
        if not health_monitor:
            result["issues"].append("Health Monitor manquant")
            return result

        rag_engine = health_monitor.get_service("rag_engine_enhanced")
        if not rag_engine:
            result["issues"].append("RAG Engine manquant")
            return result

        retriever = safe_get_attribute(rag_engine, "retriever")
        embedder = safe_get_attribute(rag_engine, "embedder")

        if not retriever or not embedder:
            result["issues"].append("Retriever ou Embedder manquant")
            return result

        # Test recherche Ross 308
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

                    # Vérifier si on trouve des documents de performance
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

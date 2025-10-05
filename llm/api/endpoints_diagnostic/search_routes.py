# -*- coding: utf-8 -*-
"""
Search diagnostic routes
Contains endpoints for document search and metadata diagnostics
"""

import time
import asyncio
import logging
from utils.types import Callable, Optional
from fastapi import APIRouter, Query

from config.config import BASE_PATH
from utils.utilities import safe_get_attribute
from api.endpoints import safe_serialize_for_json

from .helpers import (
    get_collections_info,
    get_collection_safely,
    get_rag_engine_from_health_monitor,
)

logger = logging.getLogger(__name__)


def create_search_routes(get_service: Callable) -> APIRouter:
    """
    Create search diagnostic routes

    Args:
        get_service: Function to retrieve services

    Returns:
        APIRouter instance with search endpoints
    """
    router = APIRouter()

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

            rag_engine = get_rag_engine_from_health_monitor(health_monitor)
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
                    return safe_serialize_for_json(result)

                # Recherche hybride sans filtre WHERE
                documents = await retriever.hybrid_search(
                    query_vector=embedding,
                    query_text=query,
                    top_k=limit,
                    where_filter=None,
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
        limit: int = Query(20, description="Nombre d'échantillons"),
        collection_name: Optional[str] = Query(
            None, description="Collection spécifique"
        ),
    ):
        """Analyse des métadonnées des documents pour diagnostiquer l'indexation - VERSION CORRIGÉE"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {"error": "Health monitor non disponible"}

            rag_engine = get_rag_engine_from_health_monitor(health_monitor)
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
                "collection_used": None,
            }

            try:
                if hasattr(weaviate_client, "collections"):
                    # Récupérer les informations des collections
                    collections_info = await get_collections_info(weaviate_client)

                    if "error" in collections_info:
                        result["issues"].append(collections_info["error"])
                        return safe_serialize_for_json(result)

                    # Choisir la collection à analyser
                    target_collection = None
                    target_collection_name = None

                    if collection_name:
                        # Collection spécifiée par l'utilisateur
                        target_collection = get_collection_safely(
                            weaviate_client, collection_name
                        )
                        target_collection_name = collection_name
                    else:
                        # Trouver la collection avec le plus de documents
                        best_collection_name = None
                        max_docs = 0

                        for coll_name, coll_info in collections_info.items():
                            doc_count = coll_info.get("document_count", 0)
                            if doc_count > max_docs:
                                max_docs = doc_count
                                best_collection_name = coll_name

                        if best_collection_name and max_docs > 0:
                            target_collection = get_collection_safely(
                                weaviate_client, best_collection_name
                            )
                            target_collection_name = best_collection_name

                    result["collection_used"] = target_collection_name

                    if target_collection:
                        # Échantillonner des documents
                        try:
                            sample_docs = (
                                await asyncio.get_event_loop().run_in_executor(
                                    None,
                                    lambda: target_collection.query.fetch_objects(
                                        limit=limit
                                    ),
                                )
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
                                        "genetic_line": props.get(
                                            "geneticLine", "NOT_SET"
                                        ),
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

                        except Exception as e:
                            result["issues"].append(
                                f"Erreur échantillonnage documents: {e}"
                            )

                    else:
                        result["issues"].append("Aucune collection accessible trouvée")

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
        document: str = Query(..., description="Terme spécifique à chercher")
    ):
        """Recherche un document spécifique pour diagnostiquer pourquoi il n'est pas trouvé - VERSION CORRIGÉE"""
        try:
            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {"error": "Health monitor non disponible"}

            rag_engine = get_rag_engine_from_health_monitor(health_monitor)
            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            result = {
                "search_term": document,
                "timestamp": time.time(),
                "tests_performed": [],
                "results": {},
                "recommendations": [],
            }

            # Test 1: Recherche par embedding
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
                            alpha=0.3,
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
                    dummy_embedding = [0.0] * 1536
                    docs = await retriever.hybrid_search(
                        query_vector=dummy_embedding,
                        query_text=document,
                        top_k=10,
                        where_filter=None,
                        alpha=1.0,
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

            # Test 3: Recherche directe Weaviate avec Where - VERSION CORRIGÉE
            try:
                weaviate_client = safe_get_attribute(rag_engine, "weaviate_client")
                if weaviate_client and hasattr(weaviate_client, "collections"):
                    collections_info = await get_collections_info(weaviate_client)

                    if "error" not in collections_info and collections_info:
                        # Prendre la première collection accessible
                        collection_name = next(
                            (
                                name
                                for name, info in collections_info.items()
                                if info.get("accessible", False)
                                and info.get("document_count", 0) > 0
                            ),
                            None,
                        )

                        if collection_name:
                            collection = get_collection_safely(
                                weaviate_client, collection_name
                            )
                            if collection:
                                try:
                                    # Utiliser bm25 search au lieu de fetch_objects avec where
                                    docs = (
                                        await asyncio.get_event_loop().run_in_executor(
                                            None,
                                            lambda: collection.query.bm25(
                                                query=document, limit=5
                                            ),
                                        )
                                    )

                                    result["tests_performed"].append(
                                        "weaviate_where_search"
                                    )
                                    result["results"]["weaviate_where_search"] = {
                                        "documents_found": (
                                            len(docs.objects)
                                            if docs and hasattr(docs, "objects")
                                            else 0
                                        ),
                                        "direct_match": (
                                            len(docs.objects) > 0
                                            if docs and hasattr(docs, "objects")
                                            else False
                                        ),
                                        "collection_used": collection_name,
                                        "search_method": "bm25_direct",
                                    }
                                except Exception as e:
                                    result["results"]["weaviate_where_search"] = {
                                        "error": str(e)
                                    }
                            else:
                                result["results"]["weaviate_where_search"] = {
                                    "error": "Collection inaccessible"
                                }
                        else:
                            result["results"]["weaviate_where_search"] = {
                                "error": "Aucune collection utilisable trouvée"
                            }
                    else:
                        result["results"]["weaviate_where_search"] = {
                            "error": "Erreur récupération collections"
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
                    "CRITIQUE: Document introuvable par toutes les méthodes - possiblement absent"
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

    return router

# -*- coding: utf-8 -*-
"""
Search endpoint handlers - Extracted from search_routes for complexity reduction
Each handler is a standalone async function that implements endpoint logic
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, List

from utils.utilities import safe_get_attribute
from api.endpoints import safe_serialize_for_json
from .helpers import (
    get_collections_info,
    get_collection_safely,
    get_rag_engine_from_health_monitor,
)

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS FOR SEARCH_DOCUMENTS
# ============================================================================


async def _generate_embedding_info(
    embedder, query: str
) -> tuple[Optional[list], Dict[str, Any], List[str]]:
    """Generate embedding and return embedding info, issues list"""
    issues = []
    embedding = await embedder.get_embedding(query)

    if embedding:
        embedding_info = {
            "dimension": len(embedding),
            "has_values": bool(embedding),
            "first_3_values": embedding[:3] if len(embedding) >= 3 else embedding,
        }
        return embedding, embedding_info, issues
    else:
        issues.append("Échec génération embedding")
        return None, {}, issues


def _build_doc_info(doc, index: int) -> Dict[str, Any]:
    """Build document info dict from document object"""
    return {
        "index": index,
        "score": getattr(doc, "score", 0),
        "title": getattr(doc, "metadata", {}).get("title", "Sans titre"),
        "genetic_line": getattr(doc, "metadata", {}).get("geneticLine", "unknown"),
        "document_type": getattr(doc, "metadata", {}).get("documentType", "unknown"),
        "content_preview": (
            getattr(doc, "content", "")[:200] + "..."
            if getattr(doc, "content", "")
            else "Pas de contenu"
        ),
        "metadata": getattr(doc, "metadata", {}),
    }


def _analyze_search_results(
    search_results: List[Dict], query: str
) -> tuple[Dict[str, Any], List[str]]:
    """Analyze search results and return analysis dict and issues list"""
    issues = []

    ross_docs = [
        doc for doc in search_results if "ross" in doc.get("genetic_line", "").lower()
    ]

    performance_docs = [
        doc
        for doc in search_results
        if "performance" in doc.get("title", "").lower()
        or "performance" in doc.get("content_preview", "").lower()
    ]

    analysis = {
        "contains_ross_308": len(ross_docs) > 0,
        "contains_performance_data": len(performance_docs) > 0,
        "ross_documents_count": len(ross_docs),
        "performance_documents_count": len(performance_docs),
        "average_score": (
            sum(doc["score"] for doc in search_results) / len(search_results)
            if search_results
            else 0
        ),
    }

    # Check for issues
    if not ross_docs and "ross" in query.lower():
        issues.append("PROBLÈME: Aucun document Ross trouvé malgré la recherche")

    if not performance_docs and "performance" in query.lower():
        issues.append("PROBLÈME: Aucun document de performance trouvé")

    return analysis, issues


# ============================================================================
# HELPER FUNCTIONS FOR DOCUMENT_METADATA
# ============================================================================


async def _get_target_collection(weaviate_client, collection_name: Optional[str]):
    """Get target collection for metadata analysis"""
    collections_info = await get_collections_info(weaviate_client)

    if "error" in collections_info:
        return None, None, collections_info["error"]

    target_collection = None
    target_collection_name = None

    if collection_name:
        # User-specified collection
        target_collection = get_collection_safely(weaviate_client, collection_name)
        target_collection_name = collection_name
    else:
        # Find collection with most documents
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

    return target_collection, target_collection_name, None


def _build_doc_analysis(obj) -> Dict[str, Any]:
    """Build document analysis dict from Weaviate object"""
    props = obj.properties or {}

    return {
        "uuid": str(obj.uuid) if hasattr(obj, "uuid") else "unknown",
        "genetic_line": props.get("geneticLine", "NOT_SET"),
        "title": props.get("title", "NOT_SET"),
        "document_type": props.get("documentType", "NOT_SET"),
        "category": props.get("category", "NOT_SET"),
        "language": props.get("language", "NOT_SET"),
        "has_performance_data": props.get("hasPerformanceData", False),
        "content_length": len(props.get("content", "")),
        "all_properties": list(props.keys()),
    }


def _collect_unique_values(
    props: Dict, genetic_lines: List, document_types: List
) -> None:
    """Collect unique genetic lines and document types"""
    gl = props.get("geneticLine")
    if gl and gl not in genetic_lines:
        genetic_lines.append(gl)

    dt = props.get("documentType")
    if dt and dt not in document_types:
        document_types.append(dt)


def _build_metadata_analysis(
    sample_documents: List[Dict], genetic_lines: List, document_types: List
) -> Dict[str, Any]:
    """Build metadata analysis dict"""
    return {
        "total_samples": len(sample_documents),
        "genetic_lines_variety": len(genetic_lines),
        "document_types_variety": len(document_types),
        "has_ross_308": any(
            "ross" in str(gl).lower() and "308" in str(gl).lower()
            for gl in genetic_lines
        ),
        "has_performance_docs": any(
            doc.get("has_performance_data", False) for doc in sample_documents
        ),
        "missing_genetic_line": sum(
            1 for doc in sample_documents if doc["genetic_line"] == "NOT_SET"
        ),
        "empty_titles": sum(
            1
            for doc in sample_documents
            if doc["title"] == "NOT_SET" or not doc["title"]
        ),
        "average_content_length": (
            sum(doc["content_length"] for doc in sample_documents)
            / len(sample_documents)
            if sample_documents
            else 0
        ),
    }


def _check_metadata_issues(analysis: Dict[str, Any], sample_count: int) -> List[str]:
    """Check for metadata issues and return issues list"""
    issues = []

    if not analysis["has_ross_308"]:
        issues.append("CRITIQUE: Aucun document Ross 308 trouvé dans l'échantillon")

    if not analysis["has_performance_docs"]:
        issues.append("ATTENTION: Aucun document de performance trouvé")

    if analysis["missing_genetic_line"] > sample_count * 0.1:
        issues.append(
            f"PROBLÈME: {analysis['missing_genetic_line']} documents sans geneticLine"
        )

    if analysis["empty_titles"] > sample_count * 0.1:
        issues.append(f"PROBLÈME: {analysis['empty_titles']} documents sans titre")

    if analysis["average_content_length"] < 100:
        issues.append("ATTENTION: Contenu des documents très court en moyenne")

    return issues


# ============================================================================
# HELPER FUNCTIONS FOR SEARCH_SPECIFIC
# ============================================================================


async def _test_embedding_search(retriever, embedder, document: str) -> Dict[str, Any]:
    """Test embedding search and return results"""
    try:
        embedding = await embedder.get_embedding(document)
        if embedding:
            docs = await retriever.hybrid_search(
                query_vector=embedding,
                query_text=document,
                top_k=10,
                where_filter=None,
                alpha=0.3,
            )

            return {
                "documents_found": len(docs),
                "top_3_scores": [getattr(doc, "score", 0) for doc in docs[:3]],
                "contains_search_term": any(
                    document.lower() in getattr(doc, "content", "").lower()
                    or document.lower() in str(getattr(doc, "metadata", {})).lower()
                    for doc in docs[:5]
                ),
            }
    except Exception as e:
        return {"error": str(e)}

    return {"error": "No embedding generated"}


async def _test_bm25_search(retriever, document: str) -> Dict[str, Any]:
    """Test BM25 pure search and return results"""
    try:
        dummy_embedding = [0.0] * 1536
        docs = await retriever.hybrid_search(
            query_vector=dummy_embedding,
            query_text=document,
            top_k=10,
            where_filter=None,
            alpha=1.0,
        )

        return {
            "documents_found": len(docs),
            "contains_search_term": any(
                document.lower() in getattr(doc, "content", "").lower()
                for doc in docs[:5]
            ),
        }
    except Exception as e:
        return {"error": str(e)}


async def _test_weaviate_where_search(weaviate_client, document: str) -> Dict[str, Any]:
    """Test Weaviate WHERE search and return results"""
    try:
        if not hasattr(weaviate_client, "collections"):
            return {"error": "Weaviate v3 API not supported"}

        collections_info = await get_collections_info(weaviate_client)

        if "error" in collections_info or not collections_info:
            return {"error": "Erreur récupération collections"}

        # Find first accessible collection with documents
        collection_name = next(
            (
                name
                for name, info in collections_info.items()
                if info.get("accessible", False) and info.get("document_count", 0) > 0
            ),
            None,
        )

        if not collection_name:
            return {"error": "Aucune collection utilisable trouvée"}

        collection = get_collection_safely(weaviate_client, collection_name)
        if not collection:
            return {"error": "Collection inaccessible"}

        try:
            docs = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collection.query.bm25(query=document, limit=5),
            )

            return {
                "documents_found": (
                    len(docs.objects) if docs and hasattr(docs, "objects") else 0
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
            return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}


def _build_recommendations(
    embedding_found: int, bm25_found: int, where_found: int
) -> List[str]:
    """Build recommendations based on search results"""
    recommendations = []

    if embedding_found == 0 and bm25_found == 0 and where_found == 0:
        recommendations.append(
            "CRITIQUE: Document introuvable par toutes les méthodes - possiblement absent"
        )
    elif where_found > 0 and embedding_found == 0:
        recommendations.append(
            "Document présent mais problème d'embedding - vérifier la vectorisation"
        )
    elif bm25_found > 0 and embedding_found == 0:
        recommendations.append(
            "Document présent mais embedding ne matche pas - vérifier la qualité des embeddings"
        )
    elif embedding_found > 0:
        recommendations.append(
            "Document trouvé par embedding - problème possible dans les filtres ou seuils"
        )

    return recommendations


# ============================================================================
# ENDPOINT HANDLERS
# ============================================================================


async def handle_search_documents(
    get_service, query: str, limit: int = 10
) -> Dict[str, Any]:
    """
    Handle search documents diagnostic endpoint

    Args:
        get_service: Function to retrieve services
        query: Search query
        limit: Maximum number of results

    Returns:
        Search results dict
    """
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
            # Generate embedding
            embedding, embedding_info, embed_issues = await _generate_embedding_info(
                embedder, query
            )
            result["embedding_info"] = embedding_info
            result["issues"].extend(embed_issues)

            if not embedding:
                return safe_serialize_for_json(result)

            # Hybrid search
            documents = await retriever.hybrid_search(
                query_vector=embedding,
                query_text=query,
                top_k=limit,
                where_filter=None,
                alpha=0.5,
            )

            result["documents_found"] = len(documents)

            # Build document info
            for i, doc in enumerate(documents):
                doc_info = _build_doc_info(doc, i)
                result["search_results"].append(doc_info)

            # Analyze results
            analysis, analysis_issues = _analyze_search_results(
                result["search_results"], query
            )
            result["analysis"] = analysis
            result["issues"].extend(analysis_issues)

        except Exception as e:
            result["error"] = str(e)
            result["issues"].append(f"Erreur recherche: {e}")

        return safe_serialize_for_json(result)

    except Exception as e:
        logger.error(f"Erreur search_documents: {e}")
        return {"error": str(e), "timestamp": time.time()}


async def handle_document_metadata(
    get_service, limit: int = 20, collection_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Handle document metadata diagnostic endpoint

    Args:
        get_service: Function to retrieve services
        limit: Number of document samples
        collection_name: Specific collection to analyze

    Returns:
        Metadata analysis dict
    """
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
            if not hasattr(weaviate_client, "collections"):
                result["issues"].append(
                    "API Weaviate v3 non supportée pour cette analyse"
                )
                return safe_serialize_for_json(result)

            # Get target collection
            target_collection, target_collection_name, error = (
                await _get_target_collection(weaviate_client, collection_name)
            )

            if error:
                result["issues"].append(error)
                return safe_serialize_for_json(result)

            result["collection_used"] = target_collection_name

            if not target_collection:
                result["issues"].append("Aucune collection accessible trouvée")
                return safe_serialize_for_json(result)

            # Sample documents
            try:
                sample_docs = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: target_collection.query.fetch_objects(limit=limit),
                )

                if sample_docs and sample_docs.objects:
                    for obj in sample_docs.objects:
                        doc_analysis = _build_doc_analysis(obj)
                        result["sample_documents"].append(doc_analysis)

                        # Collect unique values
                        props = obj.properties or {}
                        _collect_unique_values(
                            props,
                            result["genetic_lines_found"],
                            result["document_types_found"],
                        )

                    # Build metadata analysis
                    result["metadata_analysis"] = _build_metadata_analysis(
                        result["sample_documents"],
                        result["genetic_lines_found"],
                        result["document_types_found"],
                    )

                    # Check for issues
                    issues = _check_metadata_issues(
                        result["metadata_analysis"], len(result["sample_documents"])
                    )
                    result["issues"].extend(issues)

                else:
                    result["issues"].append(
                        "Impossible de récupérer des échantillons de documents"
                    )

            except Exception as e:
                result["issues"].append(f"Erreur échantillonnage documents: {e}")

        except Exception as e:
            result["error"] = str(e)
            result["issues"].append(f"Erreur analyse métadonnées: {e}")

        return safe_serialize_for_json(result)

    except Exception as e:
        logger.error(f"Erreur document_metadata: {e}")
        return {"error": str(e), "timestamp": time.time()}


async def handle_search_specific_document(get_service, document: str) -> Dict[str, Any]:
    """
    Handle search specific document diagnostic endpoint

    Args:
        get_service: Function to retrieve services
        document: Specific document term to search

    Returns:
        Search diagnostic dict
    """
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

        retriever = safe_get_attribute(rag_engine, "retriever")
        embedder = safe_get_attribute(rag_engine, "embedder")
        weaviate_client = safe_get_attribute(rag_engine, "weaviate_client")

        # Test 1: Embedding search
        if retriever and embedder:
            embedding_result = await _test_embedding_search(
                retriever, embedder, document
            )
            result["tests_performed"].append("embedding_search")
            result["results"]["embedding_search"] = embedding_result

        # Test 2: BM25 search
        if retriever:
            bm25_result = await _test_bm25_search(retriever, document)
            result["tests_performed"].append("bm25_search")
            result["results"]["bm25_search"] = bm25_result

        # Test 3: Weaviate WHERE search
        if weaviate_client:
            where_result = await _test_weaviate_where_search(weaviate_client, document)
            result["tests_performed"].append("weaviate_where_search")
            result["results"]["weaviate_where_search"] = where_result

        # Build recommendations
        embedding_found = (
            result["results"].get("embedding_search", {}).get("documents_found", 0)
        )
        bm25_found = result["results"].get("bm25_search", {}).get("documents_found", 0)
        where_found = (
            result["results"].get("weaviate_where_search", {}).get("documents_found", 0)
        )

        result["recommendations"] = _build_recommendations(
            embedding_found, bm25_found, where_found
        )

        return safe_serialize_for_json(result)

    except Exception as e:
        logger.error(f"Erreur search_specific_document: {e}")
        return {"error": str(e), "timestamp": time.time()}

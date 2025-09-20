# -*- coding: utf-8 -*-
"""
api/endpoints_chat.py - Endpoints de chat et streaming
Gestion des conversations, streaming SSE, réponses OOD
"""

import time
import uuid
import asyncio
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from config.config import BASE_PATH, MAX_REQUEST_SIZE, STREAM_CHUNK_LEN
from utils.utilities import (
    safe_get_attribute,
    safe_dict_get,
    sse_event,
    smart_chunk_text,
    get_out_of_domain_message,
    get_aviculture_response,
    detect_language_enhanced,
)
from .endpoints_utils import (
    safe_serialize_for_json,
    metrics_collector,
    add_to_conversation_memory,
)

logger = logging.getLogger(__name__)


def create_chat_endpoints(services: Dict[str, Any]) -> APIRouter:
    """Crée les endpoints de chat et streaming"""

    router = APIRouter()

    def get_service(name: str) -> Any:
        """Helper pour récupérer un service"""
        return services.get(name)

    # ========================================================================
    # ENDPOINT CHAT PRINCIPAL
    # ========================================================================

    @router.post(f"{BASE_PATH}/chat")
    async def chat(request: Request):
        """Chat endpoint avec vraies réponses aviculture - LOGS DEBUG NETTOYÉS"""
        total_start_time = time.time()

        try:
            # Validation de la requête
            try:
                body = await request.json()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"JSON invalide: {e}")

            message = body.get("message", "").strip()
            language = body.get("language", "").strip()
            tenant_id = body.get("tenant_id", str(uuid.uuid4())[:8])

            # Validations
            if not message:
                raise HTTPException(status_code=400, detail="Message vide")

            if len(message) > MAX_REQUEST_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Message trop long (max {MAX_REQUEST_SIZE})",
                )

            # Détection de langue si non fournie
            if not language:
                language_result = detect_language_enhanced(message)
                language = (
                    language_result.language
                    if hasattr(language_result, "language")
                    else language_result
                )

            # Validation tenant_id
            if not tenant_id or len(tenant_id) > 50:
                tenant_id = str(uuid.uuid4())[:8]

            # Logique de réponse avec services
            rag_result = None
            use_fallback = False
            fallback_reason = ""

            # Essayer le RAG Engine si disponible
            health_monitor = get_service("health_monitor")
            if health_monitor:
                rag_engine = health_monitor.get_service("rag_engine_enhanced")

                if rag_engine and safe_get_attribute(
                    rag_engine, "is_initialized", False
                ):
                    try:
                        if hasattr(rag_engine, "generate_response"):
                            try:
                                rag_result = await rag_engine.generate_response(
                                    query=message,
                                    tenant_id=tenant_id,
                                    language=language,
                                )
                                logger.info("RAG generate_response réussi")

                            except Exception as generate_error:
                                logger.warning(
                                    f"generate_response échoué: {generate_error}"
                                )
                                use_fallback = True
                                fallback_reason = (
                                    f"generate_response_failed: {str(generate_error)}"
                                )
                        else:
                            use_fallback = True
                            fallback_reason = "generate_response_not_available"

                    except Exception as e:
                        logger.error(f"Erreur générale RAG: {e}")
                        use_fallback = True
                        fallback_reason = f"rag_general_error: {str(e)}"
                else:
                    use_fallback = True
                    fallback_reason = "rag_not_initialized"
            else:
                use_fallback = True
                fallback_reason = "health_monitor_unavailable"

            # Utiliser réponses aviculture au lieu de OOD
            if use_fallback or not rag_result:
                logger.info(
                    f"Utilisation fallback aviculture - Raison: {fallback_reason}"
                )

                aviculture_response = get_aviculture_response(message, language)

                # Créer un objet résultat simulé
                class FallbackResult:
                    def __init__(self, answer, reason):
                        self.answer = answer
                        self.source = "aviculture_fallback"
                        self.confidence = 0.8
                        self.processing_time = time.time() - total_start_time
                        self.metadata = {
                            "fallback_used": True,
                            "fallback_reason": reason,
                            "source_type": "integrated_knowledge",
                        }
                        self.context_docs = []

                rag_result = FallbackResult(aviculture_response, fallback_reason)

            # Enregistrer métriques
            total_processing_time = time.time() - total_start_time
            metrics_collector.record_query(
                rag_result, "rag_enhanced", total_processing_time
            )

            # Streaming de la réponse
            async def generate_response():
                try:
                    # Informations de début avec sérialisation sécurisée
                    metadata = safe_get_attribute(rag_result, "metadata", {}) or {}
                    source = safe_get_attribute(rag_result, "source", "unknown")
                    confidence = safe_get_attribute(rag_result, "confidence", 0.5)
                    processing_time = safe_get_attribute(
                        rag_result, "processing_time", 0
                    )

                    # Convertir source enum si nécessaire
                    if hasattr(source, "value"):
                        source = source.value
                    else:
                        source = str(source)

                    start_data = {
                        "type": "start",
                        "source": source,
                        "confidence": float(confidence),
                        "processing_time": float(processing_time),
                        "fallback_used": safe_dict_get(
                            metadata, "fallback_used", False
                        ),
                        "architecture": "modular-endpoints",
                        "serialization_version": "optimized_cached",
                    }

                    # Sérialisation sécurisée du message de début
                    yield sse_event(safe_serialize_for_json(start_data))

                    # Contenu de la réponse
                    answer = safe_get_attribute(rag_result, "answer", "")
                    if not answer:
                        answer = safe_get_attribute(rag_result, "response", "")
                        if not answer:
                            answer = safe_get_attribute(rag_result, "text", "")
                            if not answer:
                                answer = get_aviculture_response(message, language)

                    if answer:
                        chunks = smart_chunk_text(str(answer), STREAM_CHUNK_LEN)
                        for i, chunk in enumerate(chunks):
                            yield sse_event(
                                {"type": "chunk", "content": chunk, "chunk_index": i}
                            )
                            await asyncio.sleep(0.01)

                    # Informations finales
                    context_docs = safe_get_attribute(rag_result, "context_docs", [])
                    if not isinstance(context_docs, list):
                        context_docs = []

                    # Extraire documents_used des métadonnées
                    documents_used = 0
                    if hasattr(rag_result, "metadata") and rag_result.metadata:
                        documents_used = rag_result.metadata.get("documents_used", 0)

                    # Si pas trouvé dans metadata, fallback sur context_docs
                    if documents_used == 0:
                        documents_used = len(context_docs)

                    # Logs debug niveau DEBUG
                    logger.debug(
                        f"DEBUG API: documents_used dans la réponse = {documents_used}"
                    )
                    logger.debug(
                        f"DEBUG API: context_docs length = {len(context_docs)}"
                    )
                    logger.debug(
                        f"DEBUG API: metadata = {getattr(rag_result, 'metadata', {})}"
                    )

                    end_data = {
                        "type": "end",
                        "total_time": total_processing_time,
                        "confidence": float(confidence),
                        "documents_used": documents_used,
                        "source": source,
                        "architecture": "modular-endpoints",
                    }

                    yield sse_event(safe_serialize_for_json(end_data))

                    # Enregistrer en mémoire si tout est OK
                    if answer and source:
                        add_to_conversation_memory(
                            tenant_id, message, str(answer), "rag_enhanced"
                        )

                except Exception as e:
                    logger.error(f"Erreur streaming: {e}")
                    yield sse_event({"type": "error", "message": str(e)})

            return StreamingResponse(generate_response(), media_type="text/plain")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur chat endpoint: {e}")
            metrics_collector.record_query(
                {"source": "error"}, "error", time.time() - total_start_time
            )
            return JSONResponse(
                status_code=500, content={"error": f"Erreur traitement: {str(e)}"}
            )

    # ========================================================================
    # ENDPOINT OOD
    # ========================================================================

    @router.post(f"{BASE_PATH}/ood")
    async def ood_endpoint(request: Request):
        """Point de terminaison pour messages hors domaine"""
        try:
            body = await request.json()
            language = body.get("language", "fr")
            message = get_out_of_domain_message(language)

            async def ood_response():
                yield sse_event(
                    {
                        "type": "start",
                        "reason": "out_of_domain",
                        "architecture": "modular-endpoints",
                    }
                )

                chunks = smart_chunk_text(message, STREAM_CHUNK_LEN)
                for chunk in chunks:
                    yield sse_event({"type": "chunk", "content": chunk})
                    await asyncio.sleep(0.05)

                yield sse_event(
                    {
                        "type": "end",
                        "confidence": 1.0,
                        "architecture": "modular-endpoints",
                    }
                )

            return StreamingResponse(ood_response(), media_type="text/plain")

        except Exception as e:
            logger.error(f"Erreur OOD endpoint: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    # ========================================================================
    # ENDPOINTS DE TEST CHAT
    # ========================================================================

    @router.post(f"{BASE_PATH}/chat/test-ross308")
    async def test_ross308_query():
        """Endpoint de test spécifique pour les requêtes Ross 308"""
        try:
            test_queries = [
                "Quel est le poids d'un poulet Ross 308 de 17 jours ?",
                "Ross 308 female performance weight table day 17",
                "broiler performance objectives Ross 308",
                "RossxRoss308 BroilerPerformanceObjectives weight",
            ]

            results = {}

            health_monitor = get_service("health_monitor")
            if not health_monitor:
                return {"error": "Health monitor non disponible"}

            rag_engine = health_monitor.get_service("rag_engine_enhanced")
            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            for query in test_queries:
                try:
                    start_time = time.time()

                    result = await rag_engine.generate_response(
                        query=query, tenant_id="test_ross308", language="fr"
                    )

                    processing_time = time.time() - start_time

                    # Analyse du résultat
                    source = getattr(result, "source", None)
                    source_value = (
                        source.value if hasattr(source, "value") else str(source)
                    )

                    metadata = getattr(result, "metadata", {}) or {}
                    docs_used = metadata.get("documents_used", 0)
                    docs_found = metadata.get("documents_found", 0)
                    confidence = getattr(result, "confidence", 0)

                    response_text = getattr(result, "answer", "") or getattr(
                        result, "response", ""
                    )

                    # Analyse du contenu
                    has_specific_data = any(
                        term in response_text.lower()
                        for term in ["gramme", "kg", "g)", "poids", "weight", "17"]
                    )

                    has_generic_response = any(
                        pattern in response_text.lower()
                        for pattern in [
                            "documents fournis ne contiennent pas",
                            "information spécifique",
                            "données générales",
                        ]
                    )

                    results[query] = {
                        "source": source_value,
                        "confidence": float(confidence),
                        "processing_time": processing_time,
                        "documents_used": docs_used,
                        "documents_found": docs_found,
                        "has_specific_data": has_specific_data,
                        "has_generic_response": has_generic_response,
                        "response_preview": (
                            response_text[:200] + "..."
                            if len(response_text) > 200
                            else response_text
                        ),
                    }

                except Exception as e:
                    results[query] = {"error": str(e), "success": False}

            # Analyse globale
            total_docs_used = sum(
                r.get("documents_used", 0)
                for r in results.values()
                if isinstance(r, dict)
            )
            queries_with_specific_data = sum(
                1 for r in results.values() if r.get("has_specific_data", False)
            )
            queries_with_generic_response = sum(
                1 for r in results.values() if r.get("has_generic_response", False)
            )

            analysis = {
                "timestamp": time.time(),
                "test_queries": test_queries,
                "results": results,
                "analysis": {
                    "total_documents_used": total_docs_used,
                    "avg_docs_per_query": total_docs_used / len(test_queries),
                    "queries_with_specific_data": queries_with_specific_data,
                    "queries_with_generic_response": queries_with_generic_response,
                    "success_rate": queries_with_specific_data / len(test_queries),
                },
                "recommendations": [],
            }

            # Recommandations basées sur les résultats
            if total_docs_used == 0:
                analysis["recommendations"].append(
                    "CRITIQUE: Aucun document utilisé - problème de récupération Weaviate"
                )
            elif queries_with_specific_data == 0:
                analysis["recommendations"].append(
                    "PROBLÈME: Aucune réponse spécifique - document Ross 308 Performance non trouvé"
                )
            elif queries_with_generic_response > len(test_queries) // 2:
                analysis["recommendations"].append(
                    "ATTENTION: Majorité de réponses génériques - vérifier indexation"
                )

            return safe_serialize_for_json(analysis)

        except Exception as e:
            logger.error(f"Erreur test_ross308_query: {e}")
            return {"error": str(e), "timestamp": time.time()}

    @router.get(f"{BASE_PATH}/chat/conversation-stats")
    async def conversation_stats():
        """Statistiques des conversations en mémoire"""
        try:
            from .endpoints_utils import conversation_memory

            stats = conversation_memory.get_stats()

            # Informations détaillées si disponibles
            detailed_stats = {**stats, "recent_tenants": [], "memory_usage_bytes": 0}

            # Échantillon des tenants récents (sans exposer les données)
            recent_count = 0
            for tenant_id, tenant_data in conversation_memory.items():
                if recent_count >= 5:  # Limite à 5 exemples
                    break

                if isinstance(tenant_data, dict):
                    detailed_stats["recent_tenants"].append(
                        {
                            "tenant_id": tenant_id[:8] + "...",  # Partiellement masqué
                            "conversation_count": len(tenant_data.get("data", [])),
                            "last_query_preview": tenant_data.get("last_query", "")[:50]
                            + "...",
                            "last_update": tenant_data.get("ts", 0),
                        }
                    )
                    recent_count += 1

            # Estimation de l'usage mémoire
            try:
                import sys

                detailed_stats["memory_usage_bytes"] = sys.getsizeof(
                    conversation_memory
                )
            except Exception:
                detailed_stats["memory_usage_bytes"] = "unknown"

            return safe_serialize_for_json(detailed_stats)

        except Exception as e:
            logger.error(f"Erreur conversation_stats: {e}")
            return {"error": str(e), "timestamp": time.time()}

    return router

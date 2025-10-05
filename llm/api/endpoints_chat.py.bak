# -*- coding: utf-8 -*-
"""
api/endpoints_chat.py - Endpoints de chat et streaming avec Système RAG JSON
Version 5.0.1 - CORRIGÉ: record_query() avec signature correcte
Le contexte conversationnel est maintenant géré par QueryRouter dans RAGEngine
"""

import time
import uuid
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse

from config.config import BASE_PATH, MAX_REQUEST_SIZE, STREAM_CHUNK_LEN
from utils.utilities import (
    safe_get_attribute,
    sse_event,
    smart_chunk_text,
    get_out_of_domain_message,
    detect_language_enhanced,
)

from .endpoints import (
    safe_serialize_for_json,
    metrics_collector,
)


from .chat_models import (
    JSONValidationRequest,
    IngestionRequest,
    ExpertQueryRequest,
)

from .chat_handlers import ChatHandlers

logger = logging.getLogger(__name__)


def create_chat_endpoints(services: Dict[str, Any]) -> APIRouter:
    """Crée les endpoints de chat et streaming avec système JSON"""

    router = APIRouter()

    # Initialiser les handlers (version simplifiée sans context_manager)
    chat_handlers = ChatHandlers(services)

    def get_service(name: str) -> Any:
        """Helper pour récupérer un service"""
        return services.get(name)

    def get_rag_engine():
        """Helper pour récupérer le RAG Engine"""
        health_monitor = get_service("health_monitor")
        if health_monitor:
            return health_monitor.get_service("rag_engine_enhanced")
        return None

    # ========================================================================
    # ENDPOINTS SYSTÈME JSON AVICOLE
    # ========================================================================

    @router.post(f"{BASE_PATH}/json/validate")
    async def validate_json_document(request: JSONValidationRequest):
        """Valide un document JSON selon les schémas avicoles"""
        start_time = time.time()

        try:
            rag_engine = get_rag_engine()
            if not rag_engine:
                raise HTTPException(status_code=503, detail="RAG Engine non disponible")

            if not hasattr(rag_engine, "validate_json_document"):
                raise HTTPException(
                    status_code=501, detail="Validation JSON non disponible"
                )

            result = await rag_engine.validate_json_document(
                json_data=request.json_data, strict_mode=request.strict_mode
            )

            response = {
                **result,
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
                "version": "5.0.1_metrics_fixed",
            }

            return JSONResponse(content=safe_serialize_for_json(response))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur validation JSON: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "valid": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                },
            )

    @router.post(f"{BASE_PATH}/json/ingest")
    async def ingest_json_documents(request: IngestionRequest):
        """Ingère des documents JSON dans le système"""
        start_time = time.time()

        try:
            rag_engine = get_rag_engine()
            if not rag_engine:
                raise HTTPException(status_code=503, detail="RAG Engine non disponible")

            if not hasattr(rag_engine, "ingest_json_documents"):
                raise HTTPException(
                    status_code=501, detail="Ingestion JSON non disponible"
                )

            result = await rag_engine.ingest_json_documents(
                json_files=request.json_files, batch_size=request.batch_size
            )

            response = {
                **result,
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
                "batch_size_used": request.batch_size,
                "force_reprocess": request.force_reprocess,
            }

            return JSONResponse(content=safe_serialize_for_json(response))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur ingestion JSON: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                },
            )

    @router.post(f"{BASE_PATH}/json/search")
    async def search_json_enhanced(
        query: str = Form(...),
        genetic_line: Optional[str] = Form(None),
        performance_metrics: Optional[str] = Form(None),
        age_range: Optional[str] = Form(None),
    ):
        """Recherche avancée dans les documents JSON avec filtres avicoles"""
        start_time = time.time()

        try:
            rag_engine = get_rag_engine()
            if not rag_engine:
                raise HTTPException(status_code=503, detail="RAG Engine non disponible")

            if not hasattr(rag_engine, "search_json_enhanced"):
                raise HTTPException(
                    status_code=501, detail="Recherche JSON non disponible"
                )

            parsed_metrics = None
            if performance_metrics:
                try:
                    parsed_metrics = json.loads(performance_metrics)
                except json.JSONDecodeError:
                    parsed_metrics = [performance_metrics]

            parsed_age_range = None
            if age_range:
                try:
                    parsed_age_range = json.loads(age_range)
                except json.JSONDecodeError:
                    logger.warning(f"Âge range invalide: {age_range}")

            results = await rag_engine.search_json_enhanced(
                query=query,
                genetic_line=genetic_line,
                performance_metrics=parsed_metrics,
                age_range=parsed_age_range,
            )

            response = {
                "success": True,
                "results": results,
                "results_count": len(results),
                "query": query,
                "filters": {
                    "genetic_line": genetic_line,
                    "performance_metrics": parsed_metrics,
                    "age_range": parsed_age_range,
                },
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
            }

            return JSONResponse(content=safe_serialize_for_json(response))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur recherche JSON: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                },
            )

    @router.post(f"{BASE_PATH}/json/upload")
    async def upload_json_files(
        files: List[UploadFile] = File(...),
        batch_size: int = Form(5),
        auto_validate: bool = Form(True),
    ):
        """Upload et traitement de fichiers JSON avicoles"""
        start_time = time.time()

        try:
            if len(files) > 50:
                raise HTTPException(
                    status_code=413, detail="Maximum 50 fichiers par upload"
                )

            json_files = []
            errors = []

            for file in files:
                try:
                    if not file.filename.endswith(".json"):
                        errors.append(
                            f"{file.filename}: Format non supporté (JSON requis)"
                        )
                        continue

                    content = await file.read()
                    json_data = json.loads(content.decode("utf-8"))

                    json_files.append(
                        {
                            "filename": file.filename,
                            "data": json_data,
                            "size_bytes": len(content),
                        }
                    )

                except json.JSONDecodeError as e:
                    errors.append(f"{file.filename}: JSON invalide - {str(e)}")
                except Exception as e:
                    errors.append(f"{file.filename}: Erreur lecture - {str(e)}")

            if not json_files:
                raise HTTPException(
                    status_code=400, detail="Aucun fichier JSON valide trouvé"
                )

            validation_results = []
            if auto_validate:
                rag_engine = get_rag_engine()
                if rag_engine and hasattr(rag_engine, "validate_json_document"):
                    for json_file in json_files:
                        try:
                            validation = await rag_engine.validate_json_document(
                                json_data=json_file["data"], strict_mode=False
                            )
                            validation_results.append(
                                {
                                    "filename": json_file["filename"],
                                    "valid": validation.get("valid", False),
                                    "errors": validation.get("errors", []),
                                    "warnings": validation.get("warnings", []),
                                }
                            )
                        except Exception as e:
                            validation_results.append(
                                {
                                    "filename": json_file["filename"],
                                    "valid": False,
                                    "error": str(e),
                                }
                            )

            ingestion_result = None
            if auto_validate and validation_results:
                valid_files = [
                    jf
                    for jf, vr in zip(json_files, validation_results)
                    if vr.get("valid", False)
                ]

                if valid_files:
                    rag_engine = get_rag_engine()
                    if rag_engine and hasattr(rag_engine, "ingest_json_documents"):
                        try:
                            ingestion_result = await rag_engine.ingest_json_documents(
                                json_files=[f["data"] for f in valid_files],
                                batch_size=batch_size,
                            )
                        except Exception as e:
                            logger.error(f"Erreur ingestion: {e}")

            response = {
                "success": True,
                "files_uploaded": len(files),
                "files_parsed": len(json_files),
                "parsing_errors": errors,
                "validation_enabled": auto_validate,
                "validation_results": validation_results,
                "ingestion_result": ingestion_result,
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
            }

            return JSONResponse(content=safe_serialize_for_json(response))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur upload JSON: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time,
                },
            )

    # ========================================================================
    # ENDPOINT CHAT PRINCIPAL - SIMPLIFIÉ
    # ========================================================================

    @router.post(f"{BASE_PATH}/chat")
    async def chat(request: Request):
        """
        Chat endpoint simplifié

        VERSION 5.0.1:
        - CORRIGÉ: Appel metrics_collector.record_query() avec signature correcte
        - Le QueryRouter dans RAGEngine gère TOUT:
          * Extraction d'entités
          * Contexte conversationnel
          * Validation complétude
          * Messages de clarification
          * Routing vers PostgreSQL/Weaviate
        - Ce endpoint fait juste l'appel et le streaming
        """
        total_start_time = time.time()

        try:
            # Parsing requête
            try:
                body = await request.json()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"JSON invalide: {e}")

            message = body.get("message", "").strip()
            tenant_id = body.get("tenant_id", str(uuid.uuid4())[:8])
            genetic_line_filter = body.get("genetic_line_filter")
            use_json_search = body.get("use_json_search", True)
            performance_context = body.get("performance_context")

            # Validation basique
            if not message:
                raise HTTPException(status_code=400, detail="Message vide")

            if len(message) > MAX_REQUEST_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Message trop long (max {MAX_REQUEST_SIZE})",
                )

            # Détection automatique de la langue
            language_result = detect_language_enhanced(message)
            detected_language = (
                language_result.language
                if hasattr(language_result, "language")
                else language_result
            )

            logger.info(
                f"Langue détectée: {detected_language} "
                f"(confiance: {getattr(language_result, 'confidence', 'N/A')})"
            )

            # Normaliser tenant_id
            if not tenant_id or len(tenant_id) > 50:
                tenant_id = str(uuid.uuid4())[:8]

            # APPEL RAG DIRECT
            # Le router gère: contexte + extraction + validation + clarification
            rag_result = await chat_handlers.generate_rag_response(
                query=message,
                tenant_id=tenant_id,
                language=detected_language,
                use_json_search=use_json_search,
                genetic_line_filter=genetic_line_filter,
                performance_context=performance_context,
            )

            # Fallback si RAG indisponible
            if not rag_result:
                rag_result = chat_handlers.create_fallback_result(
                    message=message,
                    language=detected_language,
                    fallback_reason="rag_not_available",
                    total_start_time=total_start_time,
                    use_json_search=use_json_search,
                    genetic_line_filter=genetic_line_filter,
                )

            # CORRECTION CRITIQUE: Signature correcte de record_query()
            total_processing_time = time.time() - total_start_time

            # Extraire les informations de rag_result
            source = str(getattr(rag_result, "source", "unknown"))
            confidence = float(getattr(rag_result, "confidence", 0.0))

            # Appel avec la signature correcte
            metrics_collector.record_query(
                tenant_id=tenant_id,
                query=message,
                response_time=total_processing_time,
                status="success",
                source=source,
                confidence=confidence,
                language=detected_language,
                use_json_search=use_json_search,
            )

            # Streaming de la réponse
            return StreamingResponse(
                chat_handlers.generate_streaming_response(
                    rag_result,
                    message,
                    tenant_id,
                    detected_language,
                    total_processing_time,
                ),
                media_type="text/plain",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur chat endpoint: {e}", exc_info=True)

            # CORRECTION CRITIQUE: Signature correcte pour cas d'erreur
            metrics_collector.record_query(
                tenant_id=tenant_id if "tenant_id" in locals() else "unknown",
                query=message if "message" in locals() else "error",
                response_time=time.time() - total_start_time,
                status="error",
                error_type=type(e).__name__,
                error_message=str(e),
            )

            return JSONResponse(
                status_code=500, content={"error": f"Erreur traitement: {str(e)}"}
            )

    @router.post(f"{BASE_PATH}/chat/expert")
    async def expert_chat(request: ExpertQueryRequest):
        """Endpoint de chat expert avec paramètres avancés et streaming"""
        total_start_time = time.time()

        try:
            performance_context = None
            if request.performance_metrics or request.age_range:
                performance_context = {}
                if request.performance_metrics:
                    performance_context["metrics"] = request.performance_metrics
                if request.age_range:
                    performance_context["age_range"] = request.age_range

            rag_result = await chat_handlers.generate_rag_response(
                query=request.question,
                tenant_id=request.user_id or str(uuid.uuid4())[:8],
                language=request.language,
                use_json_search=request.use_json_search,
                genetic_line_filter=request.genetic_line,
                performance_context=performance_context,
            )

            if not rag_result:
                raise HTTPException(status_code=503, detail="RAG Engine non disponible")

            async def generate_expert_response():
                try:
                    metadata = safe_get_attribute(rag_result, "metadata", {}) or {}

                    expert_metadata = {
                        "type": "expert_start",
                        "question": request.question,
                        "genetic_line_requested": request.genetic_line,
                        "performance_metrics": request.performance_metrics,
                        "age_range": request.age_range,
                        "response_format": request.response_format,
                        "json_search_used": request.use_json_search,
                        "preprocessing_enabled": True,
                        "router_managed": True,
                        "confidence": float(
                            safe_get_attribute(rag_result, "confidence", 0.5)
                        ),
                        "json_system": metadata.get("json_system", {}),
                        "architecture": "query-router-v5.0.1",
                    }

                    yield sse_event(safe_serialize_for_json(expert_metadata))

                    answer = safe_get_attribute(rag_result, "answer", "")
                    if answer:
                        if request.response_format == "ultra_concise":
                            chunks = smart_chunk_text(
                                str(answer)[:200] + "...", STREAM_CHUNK_LEN
                            )
                        elif request.response_format == "concise":
                            chunks = smart_chunk_text(
                                str(answer)[:500] + "...", STREAM_CHUNK_LEN
                            )
                        else:
                            chunks = smart_chunk_text(str(answer), STREAM_CHUNK_LEN)

                        for i, chunk in enumerate(chunks):
                            yield sse_event(
                                {
                                    "type": "expert_chunk",
                                    "content": chunk,
                                    "chunk_index": i,
                                    "format": request.response_format,
                                }
                            )
                            await asyncio.sleep(0.01)

                    end_metadata = {
                        "type": "expert_end",
                        "total_time": time.time() - total_start_time,
                        "documents_used": metadata.get("documents_used", 0),
                        "json_results_count": metadata.get("json_system", {}).get(
                            "results_count", 0
                        ),
                        "genetic_lines_detected": metadata.get("json_system", {}).get(
                            "genetic_lines_detected", []
                        ),
                        "confidence": float(
                            safe_get_attribute(rag_result, "confidence", 0.5)
                        ),
                        "response_format_applied": request.response_format,
                        "preprocessing_enabled": True,
                        "router_managed": True,
                    }

                    yield sse_event(safe_serialize_for_json(end_metadata))

                except Exception as e:
                    logger.error(f"Erreur streaming expert: {e}")
                    yield sse_event({"type": "error", "message": str(e)})

            return StreamingResponse(
                generate_expert_response(), media_type="text/plain"
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur expert chat endpoint: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Erreur traitement expert: {str(e)}"},
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
                        "architecture": "query-router-v5.0.1",
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
                        "architecture": "query-router-v5.0.1",
                    }
                )

            return StreamingResponse(ood_response(), media_type="text/plain")

        except Exception as e:
            logger.error(f"Erreur OOD endpoint: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    # ========================================================================
    # ENDPOINTS DE TEST
    # ========================================================================

    @router.post(f"{BASE_PATH}/chat/test-json-system")
    async def test_json_system():
        """Test complet du système JSON intégré"""
        try:
            test_results = {}
            rag_engine = get_rag_engine()

            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            # Test validation
            try:
                test_json = {
                    "title": "Test Ross 308 Performance",
                    "text": "Performance objectives for Ross 308 broilers at 35 days.",
                    "metadata": {"genetic_line": "ross308"},
                    "tables": [],
                }

                if hasattr(rag_engine, "validate_json_document"):
                    validation_result = await rag_engine.validate_json_document(
                        test_json
                    )
                    test_results["json_validation"] = {
                        "success": True,
                        "valid": validation_result.get("valid", False),
                        "errors": validation_result.get("errors", []),
                    }
                else:
                    test_results["json_validation"] = {
                        "success": False,
                        "reason": "Méthode non disponible",
                    }
            except Exception as e:
                test_results["json_validation"] = {"success": False, "error": str(e)}

            # Test search
            try:
                if hasattr(rag_engine, "search_json_enhanced"):
                    search_results = await rag_engine.search_json_enhanced(
                        query="Ross 308 poids 35 jours", genetic_line="ross308"
                    )
                    test_results["json_search"] = {
                        "success": True,
                        "results_count": len(search_results),
                        "has_results": len(search_results) > 0,
                    }
                else:
                    test_results["json_search"] = {
                        "success": False,
                        "reason": "Méthode non disponible",
                    }
            except Exception as e:
                test_results["json_search"] = {"success": False, "error": str(e)}

            # Test génération
            try:
                generation_result = await chat_handlers.generate_rag_response(
                    query="Quel est le poids cible Ross 308 à 35 jours ?",
                    tenant_id="test",
                    language="fr",
                    use_json_search=True,
                    genetic_line_filter="ross308",
                )

                metadata = getattr(generation_result, "metadata", {})
                json_system_info = metadata.get("json_system", {})

                test_results["json_generation"] = {
                    "success": True,
                    "json_system_used": json_system_info.get("used", False),
                    "json_results_count": json_system_info.get("results_count", 0),
                    "confidence": getattr(generation_result, "confidence", 0),
                    "has_answer": bool(getattr(generation_result, "answer", "")),
                    "preprocessing_enabled": True,
                }
            except Exception as e:
                test_results["json_generation"] = {"success": False, "error": str(e)}

            successful_tests = sum(
                1 for result in test_results.values() if result.get("success", False)
            )
            total_tests = len(test_results)

            analysis = {
                "timestamp": time.time(),
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": (
                    successful_tests / total_tests if total_tests > 0 else 0
                ),
                "test_results": test_results,
                "system_health": (
                    "OK"
                    if successful_tests == total_tests
                    else "DEGRADED" if successful_tests > 0 else "FAILED"
                ),
                "version": "5.0.1_metrics_fixed",
            }

            return safe_serialize_for_json(analysis)

        except Exception as e:
            logger.error(f"Erreur test_json_system: {e}")
            return {"error": str(e), "timestamp": time.time()}

    @router.get(f"{BASE_PATH}/chat/conversation-stats")
    async def conversation_stats():
        """Statistiques des conversations en mémoire"""
        try:
            from .utils import conversation_memory

            stats = conversation_memory.get_stats()

            detailed_stats = {**stats, "recent_tenants": [], "memory_usage_bytes": 0}

            recent_count = 0
            for tenant_id, tenant_data in conversation_memory.items():
                if recent_count >= 5:
                    break

                if isinstance(tenant_data, dict):
                    detailed_stats["recent_tenants"].append(
                        {
                            "tenant_id": tenant_id[:8] + "...",
                            "conversation_count": len(tenant_data.get("data", [])),
                            "last_query_preview": tenant_data.get("last_query", "")[:50]
                            + "...",
                            "last_update": tenant_data.get("ts", 0),
                        }
                    )
                    recent_count += 1

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

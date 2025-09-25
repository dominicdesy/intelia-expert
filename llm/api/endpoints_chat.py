# -*- coding: utf-8 -*-
"""
api/endpoints_chat.py - Endpoints de chat et streaming avec Système RAG JSON
Gestion des conversations, streaming SSE, validation JSON, ingestion avicole
Version 4.0 - Intégration complète du pipeline JSON
"""

import time
import uuid
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, HTTPException, File, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

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


# === NOUVEAUX MODÈLES PYDANTIC POUR JSON ===


class JSONValidationRequest(BaseModel):
    """Requête de validation JSON avicole"""

    json_data: Dict[str, Any] = Field(..., description="Données JSON à valider")
    strict_mode: bool = Field(False, description="Mode de validation strict")
    auto_enrich: bool = Field(
        True, description="Enrichissement automatique des métadonnées"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "json_data": {
                    "title": "Ross 308 Performance Guide",
                    "text": "Performance objectives for Ross 308 broilers...",
                    "metadata": {"genetic_line": "ross308"},
                    "tables": [],
                },
                "strict_mode": False,
                "auto_enrich": True,
            }
        }
    }


class IngestionRequest(BaseModel):
    """Requête d'ingestion de fichiers JSON"""

    json_files: List[Dict[str, Any]] = Field(..., description="Liste des fichiers JSON")
    batch_size: int = Field(5, ge=1, le=20, description="Taille des lots de traitement")
    force_reprocess: bool = Field(
        False, description="Forcer le retraitement des fichiers existants"
    )

    @field_validator("json_files")
    @classmethod
    def validate_json_files(cls, v):
        if len(v) > 100:
            raise ValueError("Maximum 100 fichiers par lot")
        return v


class ExpertQueryRequest(BaseModel):
    """Requête d'expertise avicole avec support JSON"""

    question: str = Field(
        ..., min_length=5, max_length=500, description="Question de l'utilisateur"
    )
    language: str = Field(
        "fr", pattern="^(fr|en|es|zh|ar)$", description="Langue de la réponse"
    )
    genetic_line: Optional[str] = Field(None, description="Lignée génétique spécifique")
    user_id: Optional[str] = Field(None, description="Identifiant utilisateur")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexte additionnel")
    response_format: str = Field(
        "detailed", pattern="^(ultra_concise|concise|standard|detailed)$"
    )
    # NOUVEAUX PARAMÈTRES JSON
    use_json_search: bool = Field(
        True, description="Utiliser la recherche JSON prioritaire"
    )
    performance_metrics: Optional[List[str]] = Field(
        None, description="Métriques de performance à filtrer"
    )
    age_range: Optional[Dict[str, int]] = Field(
        None, description="Plage d'âge en jours"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Quel est le poids cible à 35 jours pour du Ross 308 mâle?",
                "language": "fr",
                "genetic_line": "ross308",
                "use_json_search": True,
                "performance_metrics": ["poids", "fcr"],
                "age_range": {"min": 30, "max": 40},
            }
        }
    }


class ChatRequest(BaseModel):
    """Requête de chat étendue avec support JSON"""

    message: str = Field(
        ..., min_length=1, max_length=2000, description="Message utilisateur"
    )
    language: Optional[str] = Field(None, description="Langue de la réponse")
    tenant_id: Optional[str] = Field(None, description="Identifiant du tenant")
    # NOUVEAUX PARAMÈTRES JSON
    genetic_line_filter: Optional[str] = Field(
        None, description="Filtre lignée génétique"
    )
    use_json_search: bool = Field(True, description="Utiliser le système JSON")
    performance_context: Optional[Dict[str, Any]] = Field(
        None, description="Contexte performance"
    )


def create_chat_endpoints(services: Dict[str, Any]) -> APIRouter:
    """Crée les endpoints de chat et streaming avec système JSON"""

    router = APIRouter()

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

            # Enrichissement de la réponse
            response = {
                **result,
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
                "version": "4.0_json_integrated",
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

            # Enrichissement de la réponse
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
        performance_metrics: Optional[str] = Form(None),  # JSON string
        age_range: Optional[str] = Form(None),  # JSON string
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

            # Parsing des paramètres JSON
            parsed_metrics = None
            if performance_metrics:
                try:
                    parsed_metrics = json.loads(performance_metrics)
                except json.JSONDecodeError:
                    parsed_metrics = [performance_metrics]  # Fallback single string

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

            # Lecture et parsing des fichiers
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

            # Validation automatique si demandée
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

            # Ingestion si validation OK
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
    # ENDPOINT CHAT PRINCIPAL AMÉLIORÉ
    # ========================================================================

    @router.post(f"{BASE_PATH}/chat")
    async def chat(request: Request):
        """Chat endpoint avec système JSON intégré - LOGS DEBUG NETTOYÉS"""
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

            # NOUVEAUX PARAMÈTRES JSON
            genetic_line_filter = body.get("genetic_line_filter")
            use_json_search = body.get("use_json_search", True)
            performance_context = body.get("performance_context")

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

            # Logique de réponse avec système JSON
            rag_result = None
            use_fallback = False
            fallback_reason = ""

            # Essayer le RAG Engine avec système JSON
            rag_engine = get_rag_engine()
            if rag_engine and safe_get_attribute(rag_engine, "is_initialized", False):
                try:
                    if hasattr(rag_engine, "generate_response"):
                        try:
                            # NOUVELLE SIGNATURE avec paramètres JSON
                            rag_result = await rag_engine.generate_response(
                                query=message,
                                tenant_id=tenant_id,
                                language=language,
                                use_json_search=use_json_search,
                                genetic_line_filter=genetic_line_filter,
                                performance_context=performance_context,
                            )
                            logger.info(
                                f"RAG generate_response réussi (JSON: {use_json_search})"
                            )

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
                            "json_system_attempted": use_json_search,
                            "genetic_line_filter": genetic_line_filter,
                        }
                        self.context_docs = []

                rag_result = FallbackResult(aviculture_response, fallback_reason)

            # Enregistrer métriques
            total_processing_time = time.time() - total_start_time
            metrics_collector.record_query(
                rag_result, "rag_enhanced_json", total_processing_time
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
                        "architecture": "modular-endpoints-json",
                        "serialization_version": "optimized_cached",
                        # NOUVELLES MÉTADONNÉES JSON
                        "json_system_used": metadata.get("json_system", {}).get(
                            "used", False
                        ),
                        "json_results_count": metadata.get("json_system", {}).get(
                            "results_count", 0
                        ),
                        "genetic_line_detected": metadata.get("json_system", {}).get(
                            "genetic_line_filter"
                        ),
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
                        "architecture": "modular-endpoints-json",
                        # NOUVELLES MÉTADONNÉES FINALES
                        "json_system_used": metadata.get("json_system", {}).get(
                            "used", False
                        ),
                        "json_results_count": metadata.get("json_system", {}).get(
                            "results_count", 0
                        ),
                        "genetic_lines_detected": metadata.get("json_system", {}).get(
                            "genetic_lines_detected", []
                        ),
                    }

                    yield sse_event(safe_serialize_for_json(end_data))

                    # Enregistrer en mémoire si tout est OK
                    if answer and source:
                        add_to_conversation_memory(
                            tenant_id, message, str(answer), "rag_enhanced_json"
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

    @router.post(f"{BASE_PATH}/chat/expert")
    async def expert_chat(request: ExpertQueryRequest):
        """Endpoint de chat expert avec paramètres avancés et streaming"""
        total_start_time = time.time()

        try:
            # Conversion du contexte performance
            performance_context = None
            if request.performance_metrics or request.age_range:
                performance_context = {}
                if request.performance_metrics:
                    performance_context["metrics"] = request.performance_metrics
                if request.age_range:
                    performance_context["age_range"] = request.age_range

            # Logique de réponse avec RAG Engine
            rag_result = None
            rag_engine = get_rag_engine()

            if rag_engine and safe_get_attribute(rag_engine, "is_initialized", False):
                try:
                    rag_result = await rag_engine.generate_response(
                        query=request.question,
                        tenant_id=request.user_id or str(uuid.uuid4())[:8],
                        language=request.language,
                        use_json_search=request.use_json_search,
                        genetic_line_filter=request.genetic_line,
                        performance_context=performance_context,
                    )
                except Exception as e:
                    logger.error(f"Erreur expert chat: {e}")
                    raise HTTPException(
                        status_code=500, detail=f"Erreur traitement: {str(e)}"
                    )
            else:
                raise HTTPException(status_code=503, detail="RAG Engine non disponible")

            # Streaming de la réponse expert
            async def generate_expert_response():
                try:
                    metadata = safe_get_attribute(rag_result, "metadata", {}) or {}

                    # Métadonnées expert enrichies
                    expert_metadata = {
                        "type": "expert_start",
                        "question": request.question,
                        "genetic_line_requested": request.genetic_line,
                        "performance_metrics": request.performance_metrics,
                        "age_range": request.age_range,
                        "response_format": request.response_format,
                        "json_search_used": request.use_json_search,
                        "confidence": float(
                            safe_get_attribute(rag_result, "confidence", 0.5)
                        ),
                        "json_system": metadata.get("json_system", {}),
                        "architecture": "expert_chat_json",
                    }

                    yield sse_event(safe_serialize_for_json(expert_metadata))

                    # Contenu de la réponse
                    answer = safe_get_attribute(rag_result, "answer", "")
                    if answer:
                        # Adaptation du format de réponse
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

                    # Fin expert avec métadonnées détaillées
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
    # ENDPOINT OOD (CONSERVÉ)
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
                        "architecture": "modular-endpoints-json",
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
                        "architecture": "modular-endpoints-json",
                    }
                )

            return StreamingResponse(ood_response(), media_type="text/plain")

        except Exception as e:
            logger.error(f"Erreur OOD endpoint: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    # ========================================================================
    # ENDPOINTS DE TEST AVEC SYSTÈME JSON
    # ========================================================================

    @router.post(f"{BASE_PATH}/chat/test-json-system")
    async def test_json_system():
        """Test complet du système JSON intégré"""
        try:
            test_results = {}
            rag_engine = get_rag_engine()

            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            # Test 1: Validation JSON
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

            # Test 2: Recherche JSON
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

            # Test 3: Génération avec JSON
            try:
                generation_result = await rag_engine.generate_response(
                    query="Quel est le poids cible Ross 308 à 35 jours ?",
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
                }
            except Exception as e:
                test_results["json_generation"] = {"success": False, "error": str(e)}

            # Test 4: Status système JSON
            try:
                status = rag_engine.get_status()
                json_system_status = status.get("json_system", {})
                test_results["json_system_status"] = {
                    "available": json_system_status.get("available", False),
                    "components": json_system_status.get("components", {}),
                    "stats": json_system_status.get("stats", {}),
                }
            except Exception as e:
                test_results["json_system_status"] = {"success": False, "error": str(e)}

            # Analyse globale
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
            }

            return safe_serialize_for_json(analysis)

        except Exception as e:
            logger.error(f"Erreur test_json_system: {e}")
            return {"error": str(e), "timestamp": time.time()}

    @router.post(f"{BASE_PATH}/chat/test-ross308")
    async def test_ross308_query():
        """Endpoint de test spécifique pour les requêtes Ross 308 avec JSON"""
        try:
            test_queries = [
                "Quel est le poids d'un poulet Ross 308 de 17 jours ?",
                "Ross 308 female performance weight table day 17",
                "broiler performance objectives Ross 308",
                "RossxRoss308 BroilerPerformanceObjectives weight",
            ]

            results = {}
            rag_engine = get_rag_engine()

            if not rag_engine:
                return {"error": "RAG Engine non disponible"}

            for query in test_queries:
                try:
                    start_time = time.time()

                    # Test avec système JSON activé
                    result = await rag_engine.generate_response(
                        query=query,
                        tenant_id="test_ross308",
                        language="fr",
                        use_json_search=True,
                        genetic_line_filter="ross308",
                    )

                    processing_time = time.time() - start_time

                    # Analyse du résultat
                    source = getattr(result, "source", None)
                    source_value = (
                        source.value if hasattr(source, "value") else str(source)
                    )

                    metadata = getattr(result, "metadata", {}) or {}
                    json_system_info = metadata.get("json_system", {})
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
                        "json_system_used": json_system_info.get("used", False),
                        "json_results_count": json_system_info.get("results_count", 0),
                        "genetic_lines_detected": json_system_info.get(
                            "genetic_lines_detected", []
                        ),
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

            # Analyse globale avec système JSON
            total_docs_used = sum(
                r.get("documents_used", 0)
                for r in results.values()
                if isinstance(r, dict)
            )
            total_json_results = sum(
                r.get("json_results_count", 0)
                for r in results.values()
                if isinstance(r, dict)
            )
            queries_with_json = sum(
                1 for r in results.values() if r.get("json_system_used", False)
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
                    "total_json_results": total_json_results,
                    "avg_docs_per_query": total_docs_used / len(test_queries),
                    "queries_using_json_system": queries_with_json,
                    "queries_with_specific_data": queries_with_specific_data,
                    "queries_with_generic_response": queries_with_generic_response,
                    "success_rate": queries_with_specific_data / len(test_queries),
                    "json_system_effectiveness": queries_with_json / len(test_queries),
                },
                "recommendations": [],
            }

            # Recommandations basées sur les résultats
            if total_json_results == 0 and queries_with_json == 0:
                analysis["recommendations"].append(
                    "CRITIQUE: Système JSON non utilisé - vérifier l'intégration"
                )
            elif total_docs_used == 0:
                analysis["recommendations"].append(
                    "CRITIQUE: Aucun document utilisé - problème de récupération"
                )
            elif queries_with_specific_data == 0:
                analysis["recommendations"].append(
                    "PROBLÈME: Aucune réponse spécifique - document Ross 308 non indexé"
                )
            elif queries_with_generic_response > len(test_queries) // 2:
                analysis["recommendations"].append(
                    "ATTENTION: Majorité de réponses génériques - optimiser l'indexation JSON"
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

# -*- coding: utf-8 -*-
"""
api/endpoints_chat/chat_routes.py - Main chat endpoints
Version 5.0.2 - Chat endpoint with streaming
"""

import time
import uuid
import logging
from utils.types import Any, Callable
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from config.config import BASE_PATH, MAX_REQUEST_SIZE
from utils.utilities import (
    safe_get_attribute,
    detect_language_enhanced,
)
from ..endpoints import safe_serialize_for_json, metrics_collector
from ..chat_handlers import ChatHandlers

# NOUVEAU: Import du monitoring
from monitoring.metrics import get_metrics_collector

# VERSION TRACKING
from version import BUILD_ID

logger = logging.getLogger(__name__)


def create_chat_routes(get_service: Callable[[str], Any]) -> APIRouter:
    """
    Crée l'endpoint de chat principal

    Args:
        get_service: Fonction pour récupérer un service par nom

    Returns:
        APIRouter configuré avec l'endpoint de chat
    """
    router = APIRouter()

    # Récupérer les services nécessaires
    # Note: On suppose que get_service retourne un service, mais on a besoin du dict complet
    # Pour l'instant, on va construire les handlers avec un dict vide et voir si ça marche
    # Sinon il faudra passer le dict de services directement

    def get_rag_engine():
        """Helper pour récupérer le RAG Engine"""
        health_monitor = get_service("health_monitor")
        if health_monitor:
            return health_monitor.get_service("rag_engine_enhanced")
        return None

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

        # Créer chat_handlers ici pour avoir accès aux services
        # On va devoir récupérer tous les services nécessaires
        health_monitor = get_service("health_monitor")
        services_dict = {
            "health_monitor": health_monitor,
        }
        chat_handlers = ChatHandlers(services_dict)

        try:
            # Parsing requête
            try:
                body = await request.json()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"JSON invalide: {e}")

            message = body.get("message", "").strip()
            tenant_id = body.get("tenant_id", str(uuid.uuid4())[:8])
            conversation_id = body.get("conversation_id")  # 🆕 ID de session/conversation
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
            # Extract string from LanguageDetectionResult or use string directly
            detected_language: str = (
                language_result.language
                if hasattr(language_result, "language")
                else str(language_result)
            )

            logger.info(
                f"🔧 BUILD={BUILD_ID} | "
                f"Langue détectée: {detected_language} "
                f"(confiance: {getattr(language_result, 'confidence', 'N/A')})"
            )

            # Normaliser tenant_id
            if not tenant_id or len(tenant_id) > 50:
                tenant_id = str(uuid.uuid4())[:8]

            # APPEL RAG DIRECT
            # Le router gère: contexte + extraction + validation + clarification
            # 🆕 Passer conversation_id pour isolation mémoire
            rag_result = await chat_handlers.generate_rag_response(
                query=message,
                tenant_id=tenant_id,
                conversation_id=conversation_id,  # 🆕 ID de session
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

            # NOUVEAU: Enregistrer dans le système de monitoring
            monitoring_collector = get_metrics_collector()
            monitoring_collector.record_request(
                "/chat", total_processing_time, error=False
            )

            # Streaming de la réponse
            return StreamingResponse(
                chat_handlers.generate_streaming_response(
                    rag_result,
                    message,
                    tenant_id,
                    detected_language,
                    total_processing_time,
                    conversation_id,  # 🆕 Passer conversation_id pour mémoire
                ),
                media_type="text/plain",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur chat endpoint: {e}", exc_info=True)

            # CORRECTION CRITIQUE: Signature correcte pour cas d'erreur
            error_duration = time.time() - total_start_time
            metrics_collector.record_query(
                tenant_id=tenant_id if "tenant_id" in locals() else "unknown",
                query=message if "message" in locals() else "error",
                response_time=error_duration,
                status="error",
                error_type=type(e).__name__,
                error_message=str(e),
            )

            # NOUVEAU: Enregistrer l'erreur dans le monitoring
            monitoring_collector = get_metrics_collector()
            monitoring_collector.record_request("/chat", error_duration, error=True)

            return JSONResponse(
                status_code=500, content={"error": f"Erreur traitement: {str(e)}"}
            )

    return router

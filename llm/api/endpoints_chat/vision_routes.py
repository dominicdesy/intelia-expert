# -*- coding: utf-8 -*-
"""
api/endpoints_chat/vision_routes.py - Medical image analysis endpoints
Version 1.1.0 - Claude Vision integration for veterinary diagnostics
Multi-image support added
"""

import time
import uuid
import logging
import httpx
from typing import Optional, List
from utils.types import Any, Callable
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from config.config import BASE_PATH, MAX_REQUEST_SIZE
from utils.utilities import detect_language_enhanced
from ..endpoints import metrics_collector

# Import monitoring
from monitoring.metrics import get_metrics_collector

# Import vision analyzer
from generation.claude_vision_analyzer import create_vision_analyzer

logger = logging.getLogger(__name__)


def create_vision_routes(get_service: Callable[[str], Any]) -> APIRouter:
    """
    Crée les endpoints d'analyse d'images médicales

    Args:
        get_service: Fonction pour récupérer un service par nom

    Returns:
        APIRouter configuré avec les endpoints vision
    """
    router = APIRouter()

    @router.post(f"{BASE_PATH}/chat-with-image")
    async def chat_with_image(
        request: Request,
        files: Optional[List[UploadFile]] = File(None),
        image_url: Optional[str] = Form(None),
        message: str = Form(""),
        tenant_id: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
        use_rag_context: bool = Form(True),
    ):
        """
        Analyse d'image(s) médicale(s) avec Claude Vision + RAG context optionnel
        SUPPORT MULTI-IMAGES: Accepte maintenant 1 ou plusieurs images

        Accepte soit:
        - Un ou plusieurs fichiers images uploadés (multipart/form-data)
        - Une URL d'image (depuis DigitalOcean Spaces ou autre)

        Args:
            files: Images uploadées (optionnel, accepte plusieurs fichiers)
            image_url: URL de l'image (optionnel, prioritaire si fournie)
            message: Question de l'utilisateur sur l'image
            tenant_id: ID du tenant (optionnel)
            language: Langue de réponse (optionnel, auto-détecté si absent)
            use_rag_context: Utiliser le contexte RAG pour enrichir l'analyse

        Returns:
            JSONResponse avec l'analyse médicale
        """
        start_time = time.time()

        try:
            # Validation des paramètres
            if not files and not image_url:
                raise HTTPException(
                    status_code=400,
                    detail="Veuillez fournir soit un/des fichier(s) image(s), soit une URL d'image"
                )

            # Si message vide et images fournies, utiliser message par défaut
            if not message or not message.strip():
                images_count = len(files) if files else (1 if image_url else 0)
                if images_count > 0:
                    if images_count == 1:
                        message = "Analysez cette image et donnez un diagnostic vétérinaire détaillé."
                    else:
                        message = f"Analysez ces {images_count} images et donnez un diagnostic vétérinaire comparatif."
                    logger.info(f"[VISION] Message auto-généré: '{message}'")
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="Le message ne peut pas être vide"
                    )

            if len(message) > MAX_REQUEST_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Message trop long (max {MAX_REQUEST_SIZE})"
                )

            # Normaliser tenant_id
            tenant_id = tenant_id or str(uuid.uuid4())[:8]

            # Détection automatique de la langue si non fournie
            if not language:
                language_result = detect_language_enhanced(message)
                detected_language = (
                    language_result.language
                    if hasattr(language_result, "language")
                    else str(language_result)
                )
            else:
                detected_language = language

            # Calculer le nombre d'images
            images_count = len(files) if files else (1 if image_url else 0)

            logger.info(
                f"[VISION] Chat with {images_count} image(s) - Tenant: {tenant_id}, Language: {detected_language}, "
                f"Query: '{message[:50]}...'"
            )

            # Récupérer les images (support multi-images)
            images_data = []

            if image_url:
                # Télécharger l'image depuis l'URL (mode single image)
                logger.info(f"[VISION] Fetching image from URL: {image_url[:100]}...")

                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(image_url)
                        response.raise_for_status()

                        image_data = response.content
                        content_type = response.headers.get("content-type", "image/jpeg")

                        logger.info(f"[VISION] Image fetched - Size: {len(image_data)} bytes, Type: {content_type}")

                        images_data.append({
                            "data": image_data,
                            "content_type": content_type,
                            "filename": "url_image"
                        })

                except httpx.HTTPError as e:
                    logger.error(f"[VISION] Error fetching image from URL: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Impossible de télécharger l'image depuis l'URL: {str(e)}"
                    )

            elif files:
                # Lire les images uploadées (support multi-images)
                logger.info(f"[VISION] Reading {len(files)} uploaded file(s)")

                allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
                max_size = 10 * 1024 * 1024  # 10 MB

                for idx, file in enumerate(files):
                    content_type = file.content_type or "image/jpeg"

                    # Valider le type de fichier
                    if content_type not in allowed_types:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Type de fichier non supporté pour {file.filename}: {content_type}. Types acceptés: {', '.join(allowed_types)}"
                        )

                    image_data = await file.read()

                    # Valider la taille (max 10MB par image)
                    if len(image_data) > max_size:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Image {file.filename} trop volumineuse: {len(image_data) / 1024 / 1024:.1f}MB. Maximum: 10MB"
                        )

                    logger.info(f"[VISION] File {idx+1}/{len(files)} read - {file.filename} - Size: {len(image_data)} bytes")

                    images_data.append({
                        "data": image_data,
                        "content_type": content_type,
                        "filename": file.filename
                    })

                logger.info(f"[VISION] All {len(images_data)} file(s) processed successfully")

            # Récupérer le contexte RAG si demandé
            context_docs = []
            if use_rag_context:
                try:
                    health_monitor = get_service("health_monitor")
                    if health_monitor:
                        rag_engine = health_monitor.get_service("rag_engine_enhanced")

                        if rag_engine:
                            logger.info("[VISION] Fetching RAG context for image analysis...")

                            # Appeler le retriever pour obtenir du contexte
                            retriever = getattr(rag_engine, "retriever", None)
                            if retriever:
                                # Récupérer 3 documents pertinents
                                rag_results = await retriever.retrieve(
                                    query=message,
                                    top_k=3,
                                    language=detected_language,
                                )

                                # Convertir en format dict pour le vision analyzer
                                context_docs = [
                                    {
                                        "content": doc.content if hasattr(doc, "content") else str(doc),
                                        "metadata": doc.metadata if hasattr(doc, "metadata") else {},
                                    }
                                    for doc in rag_results[:3]
                                ]

                                logger.info(f"[VISION] RAG context retrieved - {len(context_docs)} documents")
                        else:
                            logger.warning("[VISION] RAG engine not available - continuing without context")
                except Exception as e:
                    logger.warning(f"[VISION] Error fetching RAG context: {e} - continuing without context")

            # Créer le vision analyzer
            vision_analyzer = create_vision_analyzer(language=detected_language)

            # Analyser les images (support multi-images)
            logger.info(f"[VISION] Starting Claude Vision analysis for {len(images_data)} image(s)...")

            if len(images_data) == 1:
                # Mode single image (backward compatibility)
                analysis_result = await vision_analyzer.analyze_medical_image(
                    image_data=images_data[0]["data"],
                    user_query=message,
                    content_type=images_data[0]["content_type"],
                    context_docs=context_docs if context_docs else None,
                    language=detected_language,
                )
            else:
                # Mode multi-images
                analysis_result = await vision_analyzer.analyze_multiple_medical_images(
                    images_data=images_data,
                    user_query=message,
                    context_docs=context_docs if context_docs else None,
                    language=detected_language,
                )

            # Vérifier le succès
            if not analysis_result.get("success"):
                error_msg = analysis_result.get("error", "Unknown error")
                logger.error(f"[VISION] Analysis failed: {error_msg}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur d'analyse: {error_msg}"
                )

            # Calculer le temps de traitement
            processing_time = time.time() - start_time

            # Enregistrer les métriques
            metrics_collector.record_query(
                tenant_id=tenant_id,
                query=message,
                response_time=processing_time,
                status="success",
                source="claude_vision",
                language=detected_language,
            )

            # Monitoring
            monitoring_collector = get_metrics_collector()
            monitoring_collector.record_request(
                "/chat-with-image", processing_time, error=False
            )

            logger.info(
                f"[VISION] Analysis completed successfully - Images: {len(images_data)}, Time: {processing_time:.2f}s, "
                f"Tokens: {analysis_result.get('usage', {}).get('total_tokens', 'N/A')}"
            )

            # Retourner la réponse
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "analysis": analysis_result["analysis"],
                    "metadata": {
                        "model": analysis_result.get("model", "claude-3-5-sonnet-20241022"),
                        "language": detected_language,
                        "tenant_id": tenant_id,
                        "images_count": len(images_data),
                        "processing_time": round(processing_time, 2),
                        "usage": analysis_result.get("usage", {}),
                        "rag_context_used": len(context_docs) > 0,
                        "rag_documents_count": len(context_docs),
                    }
                }
            )

        except HTTPException:
            raise

        except Exception as e:
            logger.exception(f"[VISION] Unexpected error in chat-with-image endpoint: {e}")

            # Enregistrer l'erreur
            error_duration = time.time() - start_time
            metrics_collector.record_query(
                tenant_id=tenant_id if "tenant_id" in locals() else "unknown",
                query=message if "message" in locals() else "error",
                response_time=error_duration,
                status="error",
                error_type=type(e).__name__,
                error_message=str(e),
            )

            # Monitoring
            monitoring_collector = get_metrics_collector()
            monitoring_collector.record_request(
                "/chat-with-image", error_duration, error=True
            )

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Erreur traitement: {str(e)}"
                }
            )

    @router.get(f"{BASE_PATH}/vision/health")
    async def vision_health_check():
        """
        Health check pour le service Claude Vision

        Vérifie que l'API Anthropic est accessible et configurée
        """
        try:
            # Vérifier que la clé API est configurée
            import os
            api_key = os.getenv("ANTHROPIC_API_KEY")

            if not api_key:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unavailable",
                        "message": "ANTHROPIC_API_KEY non configurée",
                        "configured": False,
                    }
                )

            # Vérifier que le module est importable
            try:
                from generation.claude_vision_analyzer import ClaudeVisionAnalyzer
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "healthy",
                        "message": "Claude Vision service disponible",
                        "configured": True,
                        "model": "claude-3-5-sonnet-20241022",
                    }
                )
            except ImportError as e:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unavailable",
                        "message": f"Module claude_vision_analyzer non disponible: {e}",
                        "configured": False,
                    }
                )

        except Exception as e:
            logger.error(f"[VISION] Health check error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": str(e),
                }
            )

    return router

# -*- coding: utf-8 -*-
"""
api/endpoints_chat/vision_routes.py - Medical image analysis endpoints
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
api/endpoints_chat/vision_routes.py - Medical image analysis endpoints
Version 1.1.0 - Claude Vision integration for veterinary diagnostics
Multi-image support added
"""

import time
import uuid
import logging
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

# Import storage service for images (optional - non-blocking if fails)
STORAGE_SERVICE_AVAILABLE = False
try:
    from services.image_storage_service import image_storage_service

    STORAGE_SERVICE_AVAILABLE = True
    logger.info("✅ Storage service loaded - images will be saved to Spaces")
except ImportError as e:
    logger.warning(
        f"⚠️ Storage service not available - images will not be saved to Spaces: {e}"
    )
    STORAGE_SERVICE_AVAILABLE = False


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
        files: List[UploadFile] = File(...),
        message: str = Form(""),
        tenant_id: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
        use_rag_context: bool = Form(True),
    ):
        """
        Analyse d'image(s) médicale(s) avec Claude Vision + RAG context optionnel

        Flux d'accumulation : L'utilisateur ajoute des images une par une dans l'interface,
        puis envoie toutes les images ensemble pour une analyse comparative.

        Args:
            files: Liste d'images uploadées (1 ou plusieurs)
            message: Question de l'utilisateur sur les images (auto-généré si vide)
            tenant_id: ID du tenant (optionnel)
            language: Langue de réponse (optionnel, auto-détecté si absent)
            use_rag_context: Utiliser le contexte RAG pour enrichir l'analyse

        Returns:
            JSONResponse avec l'analyse médicale (simple ou comparative)
        """
        start_time = time.time()

        try:
            # Validation des paramètres
            if not files or len(files) == 0:
                raise HTTPException(
                    status_code=400, detail="Veuillez fournir au moins une image"
                )

            images_count = len(files)

            # Si message vide, générer un message par défaut selon le nombre d'images
            if not message or not message.strip():
                if images_count == 1:
                    message = "Analysez cette image et donnez un diagnostic vétérinaire détaillé."
                else:
                    message = f"Analysez ces {images_count} images et donnez un diagnostic vétérinaire comparatif détaillé."
                logger.info(f"[VISION] Message auto-généré: '{message}'")

            if len(message) > MAX_REQUEST_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Message trop long (max {MAX_REQUEST_SIZE})",
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

            logger.info(
                f"[VISION] Chat with {images_count} image(s) - Tenant: {tenant_id}, Language: {detected_language}, "
                f"Query: '{message[:50]}...'"
            )

            # Lire toutes les images uploadées
            images_data = []
            allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
            max_size = 10 * 1024 * 1024  # 10 MB par image

            logger.info(f"[VISION] Reading {images_count} uploaded file(s)...")

            for idx, file in enumerate(files):
                content_type = file.content_type or "image/jpeg"

                # Valider le type de fichier
                if content_type not in allowed_types:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Type de fichier non supporté pour {file.filename}: {content_type}. Types acceptés: {', '.join(allowed_types)}",
                    )

                image_data = await file.read()

                # Valider la taille (max 10MB par image)
                if len(image_data) > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Image {file.filename} trop volumineuse: {len(image_data) / 1024 / 1024:.1f}MB. Maximum: 10MB",
                    )

                logger.info(
                    f"[VISION] File {idx+1}/{images_count} read - {file.filename} - Size: {len(image_data)} bytes"
                )

                images_data.append(
                    {
                        "data": image_data,
                        "content_type": content_type,
                        "filename": file.filename,
                    }
                )

            logger.info(f"[VISION] All {images_count} file(s) processed successfully")

            # Récupérer le contexte RAG si demandé
            context_docs = []
            if use_rag_context:
                try:
                    health_monitor = get_service("health_monitor")
                    if health_monitor:
                        rag_engine = health_monitor.get_service("rag_engine_enhanced")

                        if rag_engine:
                            logger.info(
                                "[VISION] Fetching RAG context for image analysis..."
                            )

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
                                        "content": (
                                            doc.content
                                            if hasattr(doc, "content")
                                            else str(doc)
                                        ),
                                        "metadata": (
                                            doc.metadata
                                            if hasattr(doc, "metadata")
                                            else {}
                                        ),
                                    }
                                    for doc in rag_results[:3]
                                ]

                                logger.info(
                                    f"[VISION] RAG context retrieved - {len(context_docs)} documents"
                                )
                        else:
                            logger.warning(
                                "[VISION] RAG engine not available - continuing without context"
                            )
                except Exception as e:
                    logger.warning(
                        f"[VISION] Error fetching RAG context: {e} - continuing without context"
                    )

            # Créer le vision analyzer
            vision_analyzer = create_vision_analyzer(language=detected_language)

            # Analyser les images (méthode différente selon le nombre)
            logger.info(
                f"[VISION] Starting Claude Vision analysis for {len(images_data)} image(s)..."
            )

            if len(images_data) == 1:
                # Mode single image
                analysis_result = await vision_analyzer.analyze_medical_image(
                    image_data=images_data[0]["data"],
                    user_query=message,
                    content_type=images_data[0]["content_type"],
                    context_docs=context_docs if context_docs else None,
                    language=detected_language,
                )
            else:
                # Mode multi-images (analyse comparative)
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
                    status_code=500, detail=f"Erreur d'analyse: {error_msg}"
                )

            # Upload images to DigitalOcean Spaces (permanent storage)
            uploaded_images = []
            if STORAGE_SERVICE_AVAILABLE:
                try:
                    # Extract user_id from JWT token (if available)
                    user_id = None
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        try:
                            import jwt

                            token = auth_header.replace("Bearer ", "")
                            # Decode without verification (just to get user info)
                            decoded = jwt.decode(
                                token, options={"verify_signature": False}
                            )
                            user_id = (
                                decoded.get("sub") or decoded.get("email") or tenant_id
                            )
                            logger.info(
                                f"[VISION] Extracted user_id from JWT: {user_id}"
                            )
                        except Exception as e:
                            logger.warning(f"[VISION] Failed to decode JWT: {e}")
                            user_id = tenant_id
                    else:
                        user_id = tenant_id

                    # Upload each image to Spaces
                    for idx, img_data in enumerate(images_data):
                        try:
                            upload_result = image_storage_service.upload_image_direct(
                                image_data=img_data["data"],
                                user_id=user_id,
                                source="frontend",
                                content_type=img_data["content_type"],
                                original_filename=img_data["filename"]
                                or f"image_{idx+1}.jpg",
                                metadata={
                                    "tenant_id": tenant_id,
                                    "analysis_completed": "true",
                                    "model": analysis_result.get(
                                        "model", "claude-3-5-sonnet"
                                    ),
                                },
                            )

                            if upload_result.get("success"):
                                uploaded_images.append(
                                    {
                                        "filename": img_data["filename"],
                                        "spaces_url": upload_result["spaces_url"],
                                        "spaces_key": upload_result["spaces_key"],
                                        "size_bytes": upload_result["size_bytes"],
                                    }
                                )
                                logger.info(
                                    f"[VISION] Image {idx+1}/{len(images_data)} uploaded to Spaces: {upload_result['spaces_url']}"
                                )
                            else:
                                logger.warning(
                                    f"[VISION] Failed to upload image {idx+1}: {upload_result.get('error')}"
                                )

                        except Exception as e:
                            # Non-blocking: continue even if one image fails
                            logger.error(
                                f"[VISION] Error uploading image {idx+1} to Spaces: {e}"
                            )

                    logger.info(
                        f"[VISION] Uploaded {len(uploaded_images)}/{len(images_data)} images to Spaces"
                    )

                except Exception as e:
                    # Non-blocking: analysis already succeeded
                    logger.error(f"[VISION] Error during image upload to Spaces: {e}")

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
                        "model": analysis_result.get(
                            "model", "claude-sonnet-4-5-20250929"
                        ),
                        "language": detected_language,
                        "tenant_id": tenant_id,
                        "images_count": len(images_data),
                        "processing_time": round(processing_time, 2),
                        "usage": analysis_result.get("usage", {}),
                        "rag_context_used": len(context_docs) > 0,
                        "rag_documents_count": len(context_docs),
                        "uploaded_images": uploaded_images,  # URLs des images dans Spaces
                        "images_saved_to_spaces": len(uploaded_images),
                    },
                },
            )

        except HTTPException:
            raise

        except Exception as e:
            logger.exception(
                f"[VISION] Unexpected error in chat-with-image endpoint: {e}"
            )

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
                content={"success": False, "error": f"Erreur traitement: {str(e)}"},
            )

    @router.post(f"{BASE_PATH}/analyze-session-images")
    async def analyze_session_images(
        request: Request,
        session_id: str = Form(...),
        message: str = Form(""),
        tenant_id: Optional[str] = Form(None),
        language: Optional[str] = Form(None),
        use_rag_context: bool = Form(True),
        cleanup_after: bool = Form(True),
    ):
        """
        Analyse toutes les images accumulées pour une session

        Flux: L'utilisateur a uploadé plusieurs images via /upload-temp-image,
        puis demande l'analyse groupée de toutes ces images.

        Args:
            session_id: Identifiant de session contenant les images
            message: Question de l'utilisateur (auto-généré si vide)
            tenant_id: ID du tenant (optionnel)
            language: Langue de réponse (optionnel)
            use_rag_context: Utiliser le contexte RAG
            cleanup_after: Nettoyer les images temporaires après analyse (défaut: True)

        Returns:
            JSONResponse avec l'analyse médicale
        """
        start_time = time.time()

        try:
            # Charger les images depuis le stockage temporaire
            from pathlib import Path
            import json

            temp_dir = Path("temp_images") / session_id

            if not temp_dir.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Aucune image trouvée pour la session {session_id}",
                )

            # Lire les métadonnées et charger les images
            images_data = []
            metadata_files = list(temp_dir.glob("*.json"))

            if len(metadata_files) == 0:
                raise HTTPException(
                    status_code=404, detail=f"Aucune image dans la session {session_id}"
                )

            logger.info(
                f"[VISION_SESSION] Loading {len(metadata_files)} images from session {session_id}"
            )

            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)

                    image_id = metadata["image_id"]
                    file_extension = (
                        Path(metadata["original_filename"]).suffix or ".jpg"
                    )
                    image_path = temp_dir / f"{image_id}{file_extension}"

                    if not image_path.exists():
                        logger.warning(
                            f"[VISION_SESSION] Image file not found: {image_path}"
                        )
                        continue

                    # Lire l'image
                    with open(image_path, "rb") as f:
                        image_data = f.read()

                    images_data.append(
                        {
                            "data": image_data,
                            "content_type": metadata["content_type"],
                            "filename": metadata["original_filename"],
                        }
                    )

                    logger.info(
                        f"[VISION_SESSION] Loaded image {image_id} - {metadata['original_filename']} - "
                        f"Size: {len(image_data)} bytes"
                    )

                except Exception as e:
                    logger.warning(
                        f"[VISION_SESSION] Error loading image from {metadata_file}: {e}"
                    )
                    continue

            if len(images_data) == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Aucune image valide trouvée dans la session",
                )

            images_count = len(images_data)

            # Si message vide, générer un message par défaut
            if not message or not message.strip():
                if images_count == 1:
                    message = "Analysez cette image et donnez un diagnostic vétérinaire détaillé."
                else:
                    message = f"Analysez ces {images_count} images et donnez un diagnostic vétérinaire comparatif détaillé."
                logger.info(f"[VISION_SESSION] Message auto-généré: '{message}'")

            # Normaliser tenant_id
            tenant_id = tenant_id or str(uuid.uuid4())[:8]

            # Détection automatique de la langue
            if not language:
                language_result = detect_language_enhanced(message)
                detected_language = (
                    language_result.language
                    if hasattr(language_result, "language")
                    else str(language_result)
                )
            else:
                detected_language = language

            logger.info(
                f"[VISION_SESSION] Analyzing session {session_id} - {images_count} image(s) - "
                f"Tenant: {tenant_id}, Language: {detected_language}"
            )

            # Récupérer le contexte RAG si demandé
            context_docs = []
            if use_rag_context:
                try:
                    health_monitor = get_service("health_monitor")
                    if health_monitor:
                        rag_engine = health_monitor.get_service("rag_engine_enhanced")

                        if rag_engine:
                            logger.info("[VISION_SESSION] Fetching RAG context...")

                            retriever = getattr(rag_engine, "retriever", None)
                            if retriever:
                                rag_results = await retriever.retrieve(
                                    query=message,
                                    top_k=3,
                                    language=detected_language,
                                )

                                context_docs = [
                                    {
                                        "content": (
                                            doc.content
                                            if hasattr(doc, "content")
                                            else str(doc)
                                        ),
                                        "metadata": (
                                            doc.metadata
                                            if hasattr(doc, "metadata")
                                            else {}
                                        ),
                                    }
                                    for doc in rag_results[:3]
                                ]

                                logger.info(
                                    f"[VISION_SESSION] RAG context retrieved - {len(context_docs)} documents"
                                )
                except Exception as e:
                    logger.warning(f"[VISION_SESSION] Error fetching RAG context: {e}")

            # Créer le vision analyzer
            vision_analyzer = create_vision_analyzer(language=detected_language)

            # Analyser les images
            logger.info(
                f"[VISION_SESSION] Starting Claude Vision analysis for {images_count} image(s)..."
            )

            if images_count == 1:
                # Mode single image
                analysis_result = await vision_analyzer.analyze_medical_image(
                    image_data=images_data[0]["data"],
                    user_query=message,
                    content_type=images_data[0]["content_type"],
                    context_docs=context_docs if context_docs else None,
                    language=detected_language,
                )
            else:
                # Mode multi-images (analyse comparative)
                analysis_result = await vision_analyzer.analyze_multiple_medical_images(
                    images_data=images_data,
                    user_query=message,
                    context_docs=context_docs if context_docs else None,
                    language=detected_language,
                )

            # Vérifier le succès
            if not analysis_result.get("success"):
                error_msg = analysis_result.get("error", "Unknown error")
                logger.error(f"[VISION_SESSION] Analysis failed: {error_msg}")
                raise HTTPException(
                    status_code=500, detail=f"Erreur d'analyse: {error_msg}"
                )

            # Upload images to DigitalOcean Spaces (permanent storage)
            uploaded_images = []
            if STORAGE_SERVICE_AVAILABLE:
                try:
                    # Extract user_id from JWT token (if available)
                    user_id = None
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        try:
                            import jwt

                            token = auth_header.replace("Bearer ", "")
                            decoded = jwt.decode(
                                token, options={"verify_signature": False}
                            )
                            user_id = (
                                decoded.get("sub") or decoded.get("email") or tenant_id
                            )
                            logger.info(
                                f"[VISION_SESSION] Extracted user_id from JWT: {user_id}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"[VISION_SESSION] Failed to decode JWT: {e}"
                            )
                            user_id = tenant_id
                    else:
                        user_id = tenant_id

                    # Upload each image to Spaces
                    for idx, img_data in enumerate(images_data):
                        try:
                            upload_result = image_storage_service.upload_image_direct(
                                image_data=img_data["data"],
                                user_id=user_id,
                                source="frontend_session",
                                content_type=img_data["content_type"],
                                original_filename=img_data["filename"]
                                or f"image_{idx+1}.jpg",
                                metadata={
                                    "tenant_id": tenant_id,
                                    "session_id": session_id,
                                    "analysis_completed": "true",
                                    "model": analysis_result.get(
                                        "model", "claude-3-5-sonnet"
                                    ),
                                },
                            )

                            if upload_result.get("success"):
                                uploaded_images.append(
                                    {
                                        "filename": img_data["filename"],
                                        "spaces_url": upload_result["spaces_url"],
                                        "spaces_key": upload_result["spaces_key"],
                                        "size_bytes": upload_result["size_bytes"],
                                    }
                                )
                                logger.info(
                                    f"[VISION_SESSION] Image {idx+1}/{len(images_data)} uploaded to Spaces: {upload_result['spaces_url']}"
                                )
                            else:
                                logger.warning(
                                    f"[VISION_SESSION] Failed to upload image {idx+1}: {upload_result.get('error')}"
                                )

                        except Exception as e:
                            logger.error(
                                f"[VISION_SESSION] Error uploading image {idx+1} to Spaces: {e}"
                            )

                    logger.info(
                        f"[VISION_SESSION] Uploaded {len(uploaded_images)}/{len(images_data)} images to Spaces"
                    )

                except Exception as e:
                    logger.error(
                        f"[VISION_SESSION] Error during image upload to Spaces: {e}"
                    )

            # Nettoyer les images temporaires si demandé
            if cleanup_after:
                try:
                    import shutil

                    shutil.rmtree(temp_dir)
                    logger.info(f"[VISION_SESSION] Cleaned up session {session_id}")
                except Exception as e:
                    logger.warning(f"[VISION_SESSION] Error cleaning up session: {e}")

            # Calculer le temps de traitement
            processing_time = time.time() - start_time

            # Enregistrer les métriques
            metrics_collector.record_query(
                tenant_id=tenant_id,
                query=message,
                response_time=processing_time,
                status="success",
                source="claude_vision_session",
                language=detected_language,
            )

            # Monitoring
            monitoring_collector = get_metrics_collector()
            monitoring_collector.record_request(
                "/analyze-session-images", processing_time, error=False
            )

            logger.info(
                f"[VISION_SESSION] Analysis completed - Session: {session_id}, Images: {images_count}, "
                f"Time: {processing_time:.2f}s, Tokens: {analysis_result.get('usage', {}).get('total_tokens', 'N/A')}"
            )

            # Retourner la réponse
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "analysis": analysis_result["analysis"],
                    "metadata": {
                        "model": analysis_result.get(
                            "model", "claude-sonnet-4-5-20250929"
                        ),
                        "language": detected_language,
                        "tenant_id": tenant_id,
                        "session_id": session_id,
                        "images_count": images_count,
                        "processing_time": round(processing_time, 2),
                        "usage": analysis_result.get("usage", {}),
                        "rag_context_used": len(context_docs) > 0,
                        "rag_documents_count": len(context_docs),
                        "cleaned_up": cleanup_after,
                        "uploaded_images": uploaded_images,  # URLs des images dans Spaces
                        "images_saved_to_spaces": len(uploaded_images),
                    },
                },
            )

        except HTTPException:
            raise

        except Exception as e:
            logger.exception(f"[VISION_SESSION] Unexpected error: {e}")

            error_duration = time.time() - start_time
            metrics_collector.record_query(
                tenant_id=tenant_id if "tenant_id" in locals() else "unknown",
                query=message if "message" in locals() else "error",
                response_time=error_duration,
                status="error",
                error_type=type(e).__name__,
                error_message=str(e),
            )

            monitoring_collector = get_metrics_collector()
            monitoring_collector.record_request(
                "/analyze-session-images", error_duration, error=True
            )

            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"Erreur traitement: {str(e)}"},
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
                    },
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
                        "model": "claude-sonnet-4-5-20250929",
                    },
                )
            except ImportError as e:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unavailable",
                        "message": f"Module claude_vision_analyzer non disponible: {e}",
                        "configured": False,
                    },
                )

        except Exception as e:
            logger.error(f"[VISION] Health check error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": str(e),
                },
            )

    return router

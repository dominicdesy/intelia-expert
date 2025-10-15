# -*- coding: utf-8 -*-
"""
api/endpoints_chat/temp_image_routes.py - Upload temporaire d'images pour accumulation
Version 1.0.0 - Stockage temporaire pour analyse différée multi-images
"""

import os
import time
import uuid
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from utils.types import Callable
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from config.config import BASE_PATH

logger = logging.getLogger(__name__)

# Répertoire de stockage temporaire
TEMP_IMAGES_DIR = Path("temp_images")
TEMP_IMAGES_DIR.mkdir(exist_ok=True)

# Durée de vie des images temporaires (2 heures)
TEMP_IMAGE_LIFETIME = 2 * 60 * 60


def create_temp_image_routes(get_service: Callable[[str], Any]) -> APIRouter:
    """
    Crée les endpoints pour l'upload temporaire d'images

    Flux d'accumulation :
    1. L'utilisateur upload une image → stockée temporairement avec session_id
    2. L'utilisateur upload une 2e, 3e image → toutes regroupées par session_id
    3. L'utilisateur clique "Analyser" → toutes les images sont analysées ensemble

    Args:
        get_service: Fonction pour récupérer un service par nom

    Returns:
        APIRouter configuré avec les endpoints d'upload temporaire
    """
    router = APIRouter()

    @router.post(f"{BASE_PATH}/upload-temp-image")
    async def upload_temp_image(
        request: Request,
        file: UploadFile = File(...),
        session_id: str = Form(...),
    ):
        """
        Upload une image dans le stockage temporaire

        L'image est stockée localement avec un identifiant unique et associée à une session.
        Elle sera disponible pour analyse jusqu'à ce que la session soit nettoyée.

        Args:
            file: Image à uploader
            session_id: Identifiant de session pour regrouper les images

        Returns:
            JSONResponse avec image_id, filename, size, session_id
        """
        start_time = time.time()

        try:
            # Validation du fichier
            allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
            max_size = 10 * 1024 * 1024  # 10 MB

            content_type = file.content_type or "image/jpeg"

            if content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Type de fichier non supporté: {content_type}. Types acceptés: {', '.join(allowed_types)}"
                )

            # Lire l'image
            image_data = await file.read()

            if len(image_data) > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"Image trop volumineuse: {len(image_data) / 1024 / 1024:.1f}MB. Maximum: 10MB"
                )

            # Créer le répertoire de session si nécessaire
            session_dir = TEMP_IMAGES_DIR / session_id
            session_dir.mkdir(exist_ok=True)

            # Générer un identifiant unique pour l'image
            image_id = str(uuid.uuid4())[:8]
            file_extension = Path(file.filename).suffix or ".jpg"
            temp_filename = f"{image_id}{file_extension}"
            temp_filepath = session_dir / temp_filename

            # Sauvegarder l'image
            with open(temp_filepath, "wb") as f:
                f.write(image_data)

            # Créer un fichier de métadonnées
            metadata = {
                "image_id": image_id,
                "original_filename": file.filename,
                "content_type": content_type,
                "size": len(image_data),
                "upload_time": time.time(),
                "session_id": session_id,
            }

            metadata_filepath = session_dir / f"{image_id}.json"
            import json
            with open(metadata_filepath, "w") as f:
                json.dump(metadata, f)

            processing_time = time.time() - start_time

            logger.info(
                f"[TEMP_IMAGE] Image uploaded - Session: {session_id}, Image ID: {image_id}, "
                f"Filename: {file.filename}, Size: {len(image_data)} bytes, Time: {processing_time:.2f}s"
            )

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "image_id": image_id,
                    "filename": file.filename,
                    "size": len(image_data),
                    "session_id": session_id,
                    "temp_filepath": str(temp_filepath),
                    "upload_time": metadata["upload_time"],
                }
            )

        except HTTPException:
            raise

        except Exception as e:
            logger.exception(f"[TEMP_IMAGE] Erreur upload image temporaire: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Erreur upload: {str(e)}"
                }
            )

    @router.get(f"{BASE_PATH}/temp-images/{{session_id}}")
    async def get_temp_images(session_id: str):
        """
        Récupère la liste des images uploadées pour une session

        Args:
            session_id: Identifiant de session

        Returns:
            JSONResponse avec la liste des images et leurs métadonnées
        """
        try:
            session_dir = TEMP_IMAGES_DIR / session_id

            if not session_dir.exists():
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "session_id": session_id,
                        "images": [],
                        "count": 0,
                    }
                )

            # Lister les fichiers de métadonnées
            import json
            images = []

            for metadata_file in session_dir.glob("*.json"):
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)

                    # Vérifier que l'image existe toujours
                    image_id = metadata["image_id"]
                    file_extension = Path(metadata["original_filename"]).suffix or ".jpg"
                    image_path = session_dir / f"{image_id}{file_extension}"

                    if image_path.exists():
                        images.append(metadata)
                except Exception as e:
                    logger.warning(f"[TEMP_IMAGE] Erreur lecture métadonnées {metadata_file}: {e}")
                    continue

            logger.info(f"[TEMP_IMAGE] Récupération images - Session: {session_id}, Count: {len(images)}")

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "session_id": session_id,
                    "images": images,
                    "count": len(images),
                }
            )

        except Exception as e:
            logger.exception(f"[TEMP_IMAGE] Erreur récupération images: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e)
                }
            )

    @router.delete(f"{BASE_PATH}/temp-images/{{session_id}}")
    async def delete_temp_images(session_id: str):
        """
        Supprime toutes les images temporaires d'une session

        Args:
            session_id: Identifiant de session

        Returns:
            JSONResponse confirmant la suppression
        """
        try:
            session_dir = TEMP_IMAGES_DIR / session_id

            if not session_dir.exists():
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "Aucune image à supprimer",
                        "deleted_count": 0,
                    }
                )

            # Compter les images avant suppression
            image_count = len(list(session_dir.glob("*.json")))

            # Supprimer le répertoire de session
            shutil.rmtree(session_dir)

            logger.info(f"[TEMP_IMAGE] Nettoyage session - Session: {session_id}, Deleted: {image_count}")

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"{image_count} image(s) supprimée(s)",
                    "deleted_count": image_count,
                }
            )

        except Exception as e:
            logger.exception(f"[TEMP_IMAGE] Erreur suppression images: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e)
                }
            )

    @router.post(f"{BASE_PATH}/cleanup-old-temp-images")
    async def cleanup_old_temp_images():
        """
        Nettoie les images temporaires expirées (> 2 heures)

        Endpoint à appeler périodiquement pour libérer l'espace disque

        Returns:
            JSONResponse avec le nombre de sessions nettoyées
        """
        try:
            current_time = time.time()
            deleted_sessions = 0
            deleted_images = 0

            for session_dir in TEMP_IMAGES_DIR.iterdir():
                if not session_dir.is_dir():
                    continue

                # Vérifier l'âge de la session (basé sur le fichier le plus récent)
                import json
                session_age = 0

                for metadata_file in session_dir.glob("*.json"):
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)

                        upload_time = metadata.get("upload_time", 0)
                        age = current_time - upload_time

                        if age > session_age:
                            session_age = age
                    except:
                        continue

                # Supprimer si trop vieux
                if session_age > TEMP_IMAGE_LIFETIME:
                    image_count = len(list(session_dir.glob("*.json")))
                    shutil.rmtree(session_dir)
                    deleted_sessions += 1
                    deleted_images += image_count
                    logger.info(
                        f"[TEMP_IMAGE] Session expirée nettoyée - Session: {session_dir.name}, "
                        f"Age: {session_age/3600:.1f}h, Images: {image_count}"
                    )

            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "deleted_sessions": deleted_sessions,
                    "deleted_images": deleted_images,
                    "message": f"{deleted_sessions} session(s) expirée(s) nettoyée(s)",
                }
            )

        except Exception as e:
            logger.exception(f"[TEMP_IMAGE] Erreur nettoyage: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": str(e)
                }
            )

    return router

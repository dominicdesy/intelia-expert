# -*- coding: utf-8 -*-
"""
app/api/v1/images.py - Gestion upload images médicales (ADMINISTRATIF SEULEMENT)
Version 1.0.0 - Upload S3 + métadonnées PostgreSQL
IMPORTANT: Pas d'analyse IA ici - seulement stockage et métadonnées
"""

import os
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import boto3
from botocore.exceptions import ClientError

# === LOGGING ===
logger = logging.getLogger(__name__)

# === ROUTER ===
router = APIRouter(prefix="/images", tags=["images"])

# === CONFIGURATION DIGITALOCEAN SPACES (compatible S3) ===
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET", "intelia-expert-images")
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION", "nyc3")  # nyc3, sfo3, sgp1, ams3
DO_SPACES_ENDPOINT = os.getenv("DO_SPACES_ENDPOINT", f"https://{DO_SPACES_REGION}.digitaloceanspaces.com")
DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")

# Limites de sécurité
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


# === HELPERS ===
def get_s3_client():
    """Initialise et retourne un client S3 (DigitalOcean Spaces)"""
    if not DO_SPACES_KEY or not DO_SPACES_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Configuration DigitalOcean Spaces manquante"
        )

    return boto3.client(
        's3',
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET,
        region_name=DO_SPACES_REGION
    )


def validate_image(file: UploadFile) -> tuple[bool, Optional[str]]:
    """
    Valide une image uploadée
    Returns: (is_valid, error_message)
    """
    # Vérifier le content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        return False, f"Type de fichier non supporté: {file.content_type}. Types acceptés: {', '.join(ALLOWED_CONTENT_TYPES)}"

    # Vérifier l'extension
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return False, f"Extension non supportée: {extension}. Extensions acceptées: {', '.join(ALLOWED_EXTENSIONS)}"

    # Vérifier la taille
    file.file.seek(0, 2)  # Aller à la fin
    file_size = file.file.tell()
    file.file.seek(0)  # Revenir au début

    if file_size > MAX_FILE_SIZE:
        return False, f"Fichier trop volumineux: {file_size / 1024 / 1024:.1f}MB. Maximum: {MAX_FILE_SIZE / 1024 / 1024}MB"

    if file_size == 0:
        return False, "Le fichier est vide"

    return True, None


def generate_spaces_key(user_id: str, original_filename: str) -> str:
    """
    Génère une clé Spaces unique et organisée
    Format: medical-images/{user_id}/{year}/{month}/{uuid}_{original_filename}
    """
    now = datetime.utcnow()
    unique_id = str(uuid.uuid4())

    # Nettoyer le nom de fichier original
    safe_filename = "".join(c for c in original_filename if c.isalnum() or c in ".-_")

    return f"medical-images/{user_id}/{now.year}/{now.month:02d}/{unique_id}_{safe_filename}"


# === ENDPOINTS ===
@router.post("/upload")
async def upload_medical_image(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    description: Optional[str] = Form(None),
):
    """
    Upload une image médicale vers DigitalOcean Spaces (ADMINISTRATIF - pas d'analyse IA)

    Args:
        file: Image à uploader (JPG, PNG, WEBP, max 10MB)
        user_id: ID de l'utilisateur
        description: Description optionnelle

    Returns:
        {
            "success": true,
            "image_id": "uuid",
            "url": "https://...",
            "spaces_key": "medical-images/...",
            "size_bytes": 123456
        }
    """
    try:
        logger.info(f"[BACKEND] Upload image: user={user_id}, file={file.filename}")

        # 1. Validation
        is_valid, error_msg = validate_image(file)
        if not is_valid:
            logger.warning(f"Validation échouée: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # 2. Générer clé Spaces
        spaces_key = generate_spaces_key(user_id, file.filename or "image.jpg")
        image_id = spaces_key.split('/')[-1].split('_')[0]  # Extraire UUID

        # 3. Lire le contenu
        file_content = await file.read()

        # 4. Upload vers DigitalOcean Spaces
        spaces_client = get_s3_client()

        try:
            spaces_client.put_object(
                Bucket=DO_SPACES_BUCKET,
                Key=spaces_key,
                Body=file_content,
                ContentType=file.content_type,
                Metadata={
                    "user_id": user_id,
                    "original_filename": file.filename or "unknown",
                    "upload_timestamp": datetime.utcnow().isoformat(),
                    "description": description or "",
                },
                ACL='private'  # Privé par défaut
            )

            logger.info(f"[BACKEND] Spaces upload OK: {spaces_key}")

        except ClientError as e:
            logger.error(f"[BACKEND] Erreur Spaces: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Erreur upload DigitalOcean Spaces: {str(e)}"
            )

        # 5. Générer URL signée (valide 24h)
        try:
            presigned_url = spaces_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': DO_SPACES_BUCKET, 'Key': spaces_key},
                ExpiresIn=24 * 3600  # 24 heures
            )
        except Exception as e:
            logger.error(f"[BACKEND] Erreur URL signée: {e}")
            # URL publique DO Spaces (si ACL public)
            presigned_url = f"https://{DO_SPACES_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com/{spaces_key}"

        # 6. Enregistrer métadonnées en PostgreSQL
        try:
            from app.core.database import get_db_connection

            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO medical_images
                    (image_id, user_id, s3_key, original_filename, size_bytes,
                     content_type, description, upload_timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (image_id) DO NOTHING
                """, (
                    image_id, user_id, spaces_key, file.filename,
                    len(file_content), file.content_type, description,
                    datetime.utcnow()
                ))
                conn.commit()
                cursor.close()
                logger.info(f"[BACKEND] Métadonnées enregistrées: {image_id}")
        except Exception as e:
            # Non-bloquant si table n'existe pas
            logger.warning(f"[BACKEND] Enregistrement DB échoué (non-bloquant): {e}")

        # 7. Retour succès
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "image_id": image_id,
                "url": presigned_url,
                "spaces_key": spaces_key,
                "size_bytes": len(file_content),
                "content_type": file.content_type,
                "expires_in_hours": 24,
                "message": "Image uploadée avec succès"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[BACKEND] Erreur upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{image_id}")
async def delete_medical_image(image_id: str, user_id: str):
    """Supprime une image (métadonnées DB + S3)"""
    try:
        from app.core.database import get_db_connection

        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB non disponible")

        # Récupérer s3_key et vérifier propriété
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s3_key FROM medical_images
            WHERE image_id = %s AND user_id = %s
        """, (image_id, user_id))
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Image non trouvée")

        s3_key = result[0]

        # Supprimer de DB
        cursor.execute("""
            DELETE FROM medical_images
            WHERE image_id = %s AND user_id = %s
        """, (image_id, user_id))
        conn.commit()
        cursor.close()

        # Supprimer de DigitalOcean Spaces
        spaces_client = get_s3_client()
        spaces_client.delete_object(Bucket=DO_SPACES_BUCKET, Key=s3_key)

        logger.info(f"[BACKEND] Image supprimée: {image_id}")

        return JSONResponse(content={
            "success": True,
            "message": "Image supprimée"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[BACKEND] Erreur suppression: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}")
async def list_user_images(user_id: str, limit: int = 50, offset: int = 0):
    """Liste les images d'un utilisateur"""
    try:
        if limit > 100:
            limit = 100

        from app.core.database import get_db_connection

        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB non disponible")

        cursor = conn.cursor()
        cursor.execute("""
            SELECT image_id, original_filename, size_bytes, content_type,
                   description, upload_timestamp
            FROM medical_images
            WHERE user_id = %s
            ORDER BY upload_timestamp DESC
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))

        results = cursor.fetchall()

        # Compter total
        cursor.execute("""
            SELECT COUNT(*) FROM medical_images WHERE user_id = %s
        """, (user_id,))
        total = cursor.fetchone()[0]

        cursor.close()

        images = []
        for row in results:
            images.append({
                "image_id": row[0],
                "filename": row[1],
                "size_bytes": row[2],
                "content_type": row[3],
                "description": row[4],
                "upload_timestamp": row[5].isoformat() if row[5] else None
            })

        return JSONResponse(content={
            "success": True,
            "images": images,
            "total": total,
            "limit": limit,
            "offset": offset
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[BACKEND] Erreur liste images: {e}")
        raise HTTPException(status_code=500, detail=str(e))

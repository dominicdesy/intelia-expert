# -*- coding: utf-8 -*-
"""
Service de stockage d'images vers DigitalOcean Spaces
Version pour le service LLM
"""

import os
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Configuration DigitalOcean Spaces
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET", "intelia-expert-images")
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION", "nyc3")
DO_SPACES_ENDPOINT = os.getenv("DO_SPACES_ENDPOINT", f"https://{DO_SPACES_REGION}.digitaloceanspaces.com")
DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")

# Limites
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


class ImageStorageService:
    """Service pour stocker les images sur DigitalOcean Spaces"""

    def __init__(self):
        self.bucket = DO_SPACES_BUCKET
        self.region = DO_SPACES_REGION
        self.endpoint = DO_SPACES_ENDPOINT
        self._client = None

    def _get_client(self):
        """Lazy-load S3 client"""
        if self._client is None:
            if not DO_SPACES_KEY or not DO_SPACES_SECRET:
                raise ValueError("Configuration DigitalOcean Spaces manquante (DO_SPACES_KEY/SECRET)")

            self._client = boto3.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=DO_SPACES_KEY,
                aws_secret_access_key=DO_SPACES_SECRET,
                region_name=self.region
            )
        return self._client

    def generate_image_key(self, user_id: str, source: str = "frontend", extension: str = "jpg") -> str:
        """
        Génère une clé Spaces unique pour un fichier image
        Format: images/{source}/{user_id}/{year}/{month}/{uuid}.{extension}
        """
        now = datetime.utcnow()
        unique_id = str(uuid.uuid4())

        return f"images/{source}/{user_id}/{now.year}/{now.month:02d}/{unique_id}.{extension}"

    def upload_image(
        self,
        image_data: bytes,
        spaces_key: str,
        content_type: str = "image/jpeg",
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload une image vers DigitalOcean Spaces

        Args:
            image_data: Données image (bytes)
            spaces_key: Clé Spaces (chemin dans le bucket)
            content_type: Type MIME (image/jpeg, image/png, etc.)
            metadata: Métadonnées optionnelles

        Returns:
            URL publique du fichier

        Raises:
            ValueError: Si l'image est trop volumineuse ou vide
            ClientError: Si upload échoue
        """
        # Vérifier taille
        if len(image_data) > MAX_IMAGE_SIZE:
            raise ValueError(
                f"Image trop volumineuse: {len(image_data) / 1024 / 1024:.1f}MB "
                f"(max: {MAX_IMAGE_SIZE / 1024 / 1024}MB)"
            )

        if len(image_data) == 0:
            raise ValueError("Image vide")

        client = self._get_client()

        try:
            client.put_object(
                Bucket=self.bucket,
                Key=spaces_key,
                Body=image_data,
                ContentType=content_type,
                ACL='public-read',  # Rendre accessible publiquement
                Metadata=metadata or {}
            )

            # Construire URL publique
            public_url = f"{self.endpoint}/{self.bucket}/{spaces_key}"

            logger.info(f"✅ Image uploadée vers Spaces: {spaces_key}")
            return public_url

        except ClientError as e:
            logger.error(f"❌ Erreur upload image Spaces: {e}")
            raise

    def upload_image_direct(
        self,
        image_data: bytes,
        user_id: str,
        source: str = "frontend",
        content_type: str = "image/jpeg",
        original_filename: str = "image.jpg",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload direct d'une image (déjà en mémoire) vers Spaces

        Args:
            image_data: Données image (bytes)
            user_id: ID utilisateur
            source: Source de l'image (frontend, whatsapp, etc.)
            content_type: Type MIME
            original_filename: Nom de fichier original (pour extension)
            metadata: Métadonnées additionnelles

        Returns:
            {
                "success": True,
                "spaces_url": "https://...",
                "spaces_key": "images/...",
                "size_bytes": 123456,
                "content_type": "image/jpeg"
            }
        """
        try:
            # Déterminer extension depuis filename ou content_type
            extension_map = {
                "image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
                "image/gif": "gif"
            }

            # Essayer d'obtenir extension depuis filename
            file_ext = os.path.splitext(original_filename)[1].lower().lstrip('.')
            if file_ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                extension = file_ext
            else:
                extension = extension_map.get(content_type, "jpg")

            # Générer clé Spaces
            spaces_key = self.generate_image_key(user_id, source, extension)

            # Préparer métadonnées
            upload_metadata = {
                "source": source,
                "user_id": user_id,
                "original_filename": original_filename,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            if metadata:
                upload_metadata.update(metadata)

            # Upload vers Spaces
            spaces_url = self.upload_image(image_data, spaces_key, content_type, upload_metadata)

            return {
                "success": True,
                "spaces_url": spaces_url,
                "spaces_key": spaces_key,
                "size_bytes": len(image_data),
                "content_type": content_type
            }

        except Exception as e:
            logger.error(f"❌ Erreur upload_image_direct: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Instance singleton
image_storage_service = ImageStorageService()

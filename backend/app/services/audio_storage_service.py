# -*- coding: utf-8 -*-
"""
Service de stockage audio vers DigitalOcean Spaces
Télécharge les fichiers audio (WhatsApp/Twilio) et les stocke de façon permanente
"""

import os
import logging
import uuid
import httpx
from datetime import datetime
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# === CONFIGURATION DIGITALOCEAN SPACES ===
DO_SPACES_BUCKET = os.getenv("DO_SPACES_BUCKET", "intelia-expert-images")  # Même bucket que les images
DO_SPACES_REGION = os.getenv("DO_SPACES_REGION", "nyc3")
DO_SPACES_ENDPOINT = os.getenv("DO_SPACES_ENDPOINT", f"https://{DO_SPACES_REGION}.digitaloceanspaces.com")
DO_SPACES_KEY = os.getenv("DO_SPACES_KEY")
DO_SPACES_SECRET = os.getenv("DO_SPACES_SECRET")

# Limites
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB (WhatsApp max ~16MB)


class AudioStorageService:
    """Service pour stocker les fichiers audio sur DigitalOcean Spaces"""

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

    def generate_audio_key(self, user_id: str, source: str = "whatsapp", extension: str = "ogg") -> str:
        """
        Génère une clé Spaces unique pour un fichier audio
        Format: audio/{source}/{user_id}/{year}/{month}/{uuid}.{extension}

        Args:
            user_id: ID utilisateur
            source: Source de l'audio (whatsapp, voice_realtime, etc.)
            extension: Extension du fichier (ogg, mp3, m4a, wav)

        Returns:
            Clé Spaces (ex: "audio/whatsapp/user123/2025/10/abc-def.ogg")
        """
        now = datetime.utcnow()
        unique_id = str(uuid.uuid4())

        return f"audio/{source}/{user_id}/{now.year}/{now.month:02d}/{unique_id}.{extension}"

    async def download_from_url(
        self,
        url: str,
        auth: Optional[tuple] = None,
        timeout: int = 30
    ) -> tuple[bytes, str]:
        """
        Télécharge un fichier audio depuis une URL (ex: Twilio)

        Args:
            url: URL du fichier à télécharger
            auth: Tuple (username, password) pour authentification HTTP
            timeout: Timeout en secondes

        Returns:
            (audio_data, content_type)

        Raises:
            httpx.HTTPError: Si téléchargement échoue
        """
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            if auth:
                response = await client.get(url, auth=auth)
            else:
                response = await client.get(url)

            response.raise_for_status()

            audio_data = response.content
            content_type = response.headers.get("Content-Type", "audio/ogg")

            # Vérifier taille
            if len(audio_data) > MAX_AUDIO_SIZE:
                raise ValueError(f"Audio trop volumineux: {len(audio_data) / 1024 / 1024:.1f}MB (max: {MAX_AUDIO_SIZE / 1024 / 1024}MB)")

            if len(audio_data) == 0:
                raise ValueError("Audio vide")

            logger.info(f"✅ Audio téléchargé: {len(audio_data)} bytes, type: {content_type}")
            return audio_data, content_type

    def upload_audio(
        self,
        audio_data: bytes,
        spaces_key: str,
        content_type: str = "audio/ogg",
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload un fichier audio vers DigitalOcean Spaces

        Args:
            audio_data: Données audio (bytes)
            spaces_key: Clé Spaces (chemin dans le bucket)
            content_type: Type MIME (audio/ogg, audio/mpeg, etc.)
            metadata: Métadonnées optionnelles

        Returns:
            URL publique du fichier

        Raises:
            ClientError: Si upload échoue
        """
        client = self._get_client()

        try:
            client.put_object(
                Bucket=self.bucket,
                Key=spaces_key,
                Body=audio_data,
                ContentType=content_type,
                ACL='public-read',  # Rendre accessible publiquement
                Metadata=metadata or {}
            )

            # Construire URL publique
            public_url = f"{self.endpoint}/{self.bucket}/{spaces_key}"

            logger.info(f"✅ Audio uploadé vers Spaces: {spaces_key}")
            return public_url

        except ClientError as e:
            logger.error(f"❌ Erreur upload Spaces: {e}")
            raise

    async def download_and_upload(
        self,
        source_url: str,
        user_id: str,
        source: str = "whatsapp",
        auth: Optional[tuple] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Télécharge un audio depuis une URL et l'uploade vers Spaces (opération complète)

        Args:
            source_url: URL source (ex: Twilio)
            user_id: ID utilisateur
            source: Source de l'audio (whatsapp, voice_realtime)
            auth: Authentification pour téléchargement
            metadata: Métadonnées additionnelles

        Returns:
            {
                "success": True,
                "spaces_url": "https://...",
                "spaces_key": "audio/...",
                "size_bytes": 123456,
                "content_type": "audio/ogg"
            }
        """
        try:
            # 1. Télécharger depuis source
            audio_data, content_type = await self.download_from_url(source_url, auth=auth)

            # 2. Déterminer extension
            extension_map = {
                "audio/ogg": "ogg",
                "audio/mpeg": "mp3",
                "audio/mp4": "m4a",
                "audio/x-m4a": "m4a",
                "audio/wav": "wav"
            }
            extension = extension_map.get(content_type, "ogg")

            # 3. Générer clé Spaces
            spaces_key = self.generate_audio_key(user_id, source, extension)

            # 4. Préparer métadonnées
            upload_metadata = {
                "source": source,
                "user_id": user_id,
                "original_url": source_url,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            if metadata:
                upload_metadata.update(metadata)

            # 5. Upload vers Spaces
            spaces_url = self.upload_audio(audio_data, spaces_key, content_type, upload_metadata)

            return {
                "success": True,
                "spaces_url": spaces_url,
                "spaces_key": spaces_key,
                "size_bytes": len(audio_data),
                "content_type": content_type
            }

        except Exception as e:
            logger.error(f"❌ Erreur download_and_upload: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Instance singleton
audio_storage_service = AudioStorageService()

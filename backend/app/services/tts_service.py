# -*- coding: utf-8 -*-
"""
Service de synthèse vocale (Text-to-Speech) avec OpenAI
Génère des réponses audio pour WhatsApp
"""

import os
import logging
from typing import Optional, Dict, Any
from io import BytesIO

import openai

logger = logging.getLogger(__name__)

# Configuration OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuration TTS
DEFAULT_VOICE = "alloy"  # Voix neutre et claire
# Voix disponibles: alloy, echo, fable, onyx, nova, shimmer
DEFAULT_MODEL = "tts-1"  # Plus rapide et économique que tts-1-hd


class TTSService:
    """Service de synthèse vocale avec OpenAI TTS"""

    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self._client = None

    def _get_client(self):
        """Lazy-load OpenAI client"""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY non configurée")

            self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def generate_speech(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        model: str = DEFAULT_MODEL,
        speed: float = 1.0
    ) -> bytes:
        """
        Génère un fichier audio à partir du texte

        Args:
            text: Texte à synthétiser (max 4096 caractères pour tts-1)
            voice: Voix à utiliser (alloy, echo, fable, onyx, nova, shimmer)
            model: Modèle TTS (tts-1 ou tts-1-hd)
            speed: Vitesse de lecture (0.25 à 4.0, défaut: 1.0)

        Returns:
            bytes: Données audio au format MP3

        Raises:
            ValueError: Si les paramètres sont invalides
            Exception: Si la génération échoue
        """
        # Validation
        if not text or not text.strip():
            raise ValueError("Le texte ne peut pas être vide")

        if len(text) > 4096:
            logger.warning(f"⚠️ Texte trop long ({len(text)} chars), troncature à 4096")
            text = text[:4096]

        if speed < 0.25 or speed > 4.0:
            raise ValueError("La vitesse doit être entre 0.25 et 4.0")

        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        if voice not in valid_voices:
            raise ValueError(f"Voix invalide. Choisir parmi: {', '.join(valid_voices)}")

        try:
            logger.info(f"🔊 Generating TTS audio - Voice: {voice}, Length: {len(text)} chars")

            client = self._get_client()

            # Appeler l'API TTS
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speed,
                response_format="mp3"  # Format compatible WhatsApp
            )

            # Lire les données audio
            audio_data = response.read()

            logger.info(f"✅ TTS audio generated - Size: {len(audio_data)} bytes")

            return audio_data

        except Exception as e:
            logger.error(f"❌ Erreur génération TTS: {e}", exc_info=True)
            raise

    def generate_speech_stream(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        model: str = DEFAULT_MODEL,
        speed: float = 1.0
    ):
        """
        Génère un stream audio (pour streaming en temps réel)

        Args:
            text: Texte à synthétiser
            voice: Voix à utiliser
            model: Modèle TTS
            speed: Vitesse de lecture

        Yields:
            bytes: Chunks audio au format MP3
        """
        # Validation
        if not text or not text.strip():
            raise ValueError("Le texte ne peut pas être vide")

        if len(text) > 4096:
            logger.warning(f"⚠️ Texte trop long ({len(text)} chars), troncature à 4096")
            text = text[:4096]

        try:
            logger.info(f"🔊 Generating TTS audio stream - Voice: {voice}")

            client = self._get_client()

            # Stream TTS
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speed,
                response_format="mp3"
            )

            # Stream les chunks
            for chunk in response.iter_bytes(chunk_size=4096):
                yield chunk

            logger.info(f"✅ TTS audio stream completed")

        except Exception as e:
            logger.error(f"❌ Erreur génération TTS stream: {e}", exc_info=True)
            raise


# Instance singleton
tts_service = TTSService()


# Helper pour usage simple
def text_to_speech(text: str, voice: str = DEFAULT_VOICE) -> bytes:
    """
    Helper simple pour générer de l'audio à partir du texte

    Args:
        text: Texte à synthétiser
        voice: Voix à utiliser (défaut: alloy)

    Returns:
        bytes: Données audio MP3
    """
    return tts_service.generate_speech(text, voice=voice)

# app/api/v1/whatsapp_webhooks.py
# -*- coding: utf-8 -*-
"""
WhatsApp Webhook Handler via Twilio
Traite les messages WhatsApp entrants et envoie les réponses
Version: 2.3 - Message truncation + rate limiting fixes
"""

import os
import logging
import httpx
import time
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException, Form
from twilio.rest import Client
from twilio.request_validator import RequestValidator

# Supabase client for user lookup
try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Import JWT token creation from auth module
try:
    from .auth import create_access_token
    AUTH_AVAILABLE = True
except ImportError:
    logger_init = logging.getLogger(__name__)
    logger_init.error("❌ Failed to import create_access_token from auth")
    AUTH_AVAILABLE = False

# Import i18n system for translations
from app.utils.i18n import t

# Import conversation service for database storage
from app.services.conversation_service import conversation_service

# Import audio storage service for permanent audio storage
from app.services.audio_storage_service import audio_storage_service

router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhooks"])
logger = logging.getLogger(__name__)

# Configuration Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+15075195932")

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Configuration LLM service (microservices architecture)
# Use internal URL if available (for service-to-service communication)
# Otherwise fall back to public URL
LLM_SERVICE_URL = os.getenv("LLM_INTERNAL_URL") or os.getenv("LLM_SERVICE_URL", "https://expert.intelia.com/llm")
LLM_CHAT_ENDPOINT = f"{LLM_SERVICE_URL}/chat"

# Initialiser le client Twilio
twilio_client = None
request_validator = None

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    request_validator = RequestValidator(TWILIO_AUTH_TOKEN)
    logger.info("✅ Twilio client initialized")
else:
    logger.warning("⚠️ Twilio credentials not configured - WhatsApp disabled")

logger.info(f"✅ LLM service configured at: {LLM_CHAT_ENDPOINT}")


# ==================== HELPERS ====================

def detect_language(text: str) -> str:
    """
    Détecte la langue du texte (simple détection basée sur des mots-clés communs)
    Fallback: français par défaut

    Args:
        text: Texte à analyser

    Returns:
        Code langue ISO (en, fr, es, de, etc.)
    """
    if not text:
        return "fr"

    text_lower = text.lower()

    # Dictionnaire de mots-clés pour chaque langue
    language_keywords = {
        "en": ["the", "what", "how", "when", "where", "why", "is", "are", "can", "could", "would"],
        "fr": ["le", "la", "les", "est", "sont", "comment", "quand", "pourquoi", "quel", "quelle"],
        "es": ["el", "la", "los", "las", "es", "son", "cómo", "cuándo", "por qué", "qué"],
        "de": ["der", "die", "das", "ist", "sind", "wie", "wann", "warum", "was"],
        "it": ["il", "la", "gli", "è", "sono", "come", "quando", "perché", "cosa"],
        "pt": ["o", "a", "os", "as", "é", "são", "como", "quando", "por que", "o que"],
        "nl": ["de", "het", "is", "zijn", "hoe", "wanneer", "waarom", "wat"],
        "pl": ["jest", "są", "jak", "kiedy", "dlaczego", "co"],
        "ar": ["ما", "كيف", "متى", "لماذا", "هل", "هو", "هي"],
        "hi": ["क्या", "कैसे", "कब", "क्यों", "है", "हैं"],
        "ja": ["は", "です", "ます", "何", "どう", "いつ", "なぜ"],
        "zh": ["是", "的", "什么", "怎么", "为什么", "吗"],
        "id": ["adalah", "apa", "bagaimana", "kapan", "mengapa"],
        "th": ["คือ", "อะไร", "อย่างไร", "เมื่อไหร่", "ทำไม"],
        "tr": ["ne", "nasıl", "ne zaman", "neden", "mi", "mı"],
        "vi": ["là", "gì", "như thế nào", "khi nào", "tại sao"]
    }

    # Compter les correspondances pour chaque langue
    scores = {}
    for lang, keywords in language_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            scores[lang] = score

    # Retourner la langue avec le score le plus élevé
    if scores:
        return max(scores, key=scores.get)

    # Fallback: français
    return "fr"


def get_acknowledgment_message(message_type: str, text: str = "") -> str:
    """
    Obtient le message d'accusé de réception approprié dans la langue détectée

    Args:
        message_type: Type de message ("text", "image", "audio")
        text: Texte du message (pour détecter la langue)

    Returns:
        Message d'accusé de réception dans la langue appropriée
    """
    # Détecter la langue
    lang = detect_language(text) if text else "en"

    # Mapper le type de message vers la clé de traduction
    translation_keys = {
        "text": "whatsapp.analyzingText",
        "image": "whatsapp.analyzingImage",
        "audio": "whatsapp.analyzingAudio"
    }

    # Obtenir la clé de traduction appropriée
    translation_key = translation_keys.get(message_type, "whatsapp.analyzingText")

    # Retourner la traduction dans la langue détectée
    return t(translation_key, lang)


def create_whatsapp_user_token(user_info: Dict[str, Any]) -> Optional[str]:
    """
    Crée un JWT token pour l'utilisateur WhatsApp afin d'authentifier les appels au service LLM

    Args:
        user_info: Informations utilisateur depuis Supabase

    Returns:
        JWT token ou None si erreur
    """
    if not AUTH_AVAILABLE:
        logger.error("❌ Auth module not available - cannot create token")
        return None

    try:
        # Créer le payload du token (même format que login normal)
        token_data = {
            "sub": user_info.get("user_email"),  # Subject = email
            "email": user_info.get("user_email"),
            "user_type": user_info.get("user_type", "user"),
            "plan": user_info.get("plan_name", "essential"),
            "whatsapp": True,  # Flag pour identifier les appels WhatsApp
        }

        # Créer le token avec expiration de 10 minutes (temps de traitement LLM)
        token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=10)
        )

        logger.info(f"✅ JWT token created for WhatsApp user: {user_info.get('user_email')}")
        return token

    except Exception as e:
        logger.error(f"❌ Error creating WhatsApp user token: {e}", exc_info=True)
        return None


def get_user_by_whatsapp_number(whatsapp_number: str) -> Optional[Dict[str, Any]]:
    """
    Récupère l'utilisateur associé à un numéro WhatsApp depuis Supabase

    Args:
        whatsapp_number: Numéro WhatsApp (format: whatsapp:+1234567890)

    Returns:
        Dict avec les infos utilisateur ou None si non trouvé
    """
    try:
        if not SUPABASE_AVAILABLE or not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            logger.error("❌ Supabase not configured for WhatsApp user lookup")
            return None

        # Normaliser le numéro (enlever le préfixe whatsapp:)
        clean_number = whatsapp_number.replace("whatsapp:", "").strip()

        # Créer client Supabase
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # Chercher l'utilisateur par numéro WhatsApp
        response = supabase.table("users").select(
            "id, email, whatsapp_number, first_name, last_name, plan, user_type"
        ).eq("whatsapp_number", clean_number).execute()

        if response.data and len(response.data) > 0:
            user = response.data[0]
            logger.info(f"✅ User found for WhatsApp: {user.get('email')}")
            return {
                "user_id": str(user.get("id")),  # UUID as string for conversation service
                "user_email": user.get("email"),
                "whatsapp_number": user.get("whatsapp_number"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "plan_name": user.get("plan", "essential"),
                "user_type": user.get("user_type"),
                "whatsapp_verified": True  # Si le numéro est dans la DB, il est considéré vérifié
            }
        else:
            logger.warning(f"⚠️ No user found for WhatsApp: {clean_number}")
            return None

    except Exception as e:
        logger.error(f"❌ Error getting user by WhatsApp from Supabase: {e}")
        return None


# NOTE: link_whatsapp_to_user function removed - WhatsApp numbers are now
# managed directly in the Supabase users table via the user profile update endpoint


# ==================== RAG INTEGRATION VIA HTTP (MICROSERVICES) ====================

async def handle_text_message(
    from_number: str,
    body: str,
    user_info: Dict[str, Any],
    conversation_id: Optional[str] = None,
    media_url: Optional[str] = None,
    media_type: Optional[str] = None
) -> str:
    """
    Traite un message texte WhatsApp via appel HTTP au service LLM

    VERSION 2.1 - Microservices Architecture:
    - Appel HTTP au service LLM (même endpoint que frontend)
    - Support complet RAG avec QueryRouter
    - Historique de conversation via ConversationMemory
    - Chain of Thought (COT) analysis
    - Extraction d'entités et validation
    - Messages de clarification intelligents

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        body: Contenu du message
        user_info: Informations de l'utilisateur
        conversation_id: ID de conversation pour isoler l'historique

    Returns:
        Réponse de l'assistant AI (complète, collectée depuis le stream)
    """
    try:
        user_email = user_info.get("user_email")
        user_name = user_info.get("first_name", "")

        # Utiliser le numéro WhatsApp comme tenant_id (identifiant utilisateur unique)
        tenant_id = from_number.replace("whatsapp:", "").strip()

        # Si pas de conversation_id fourni, créer un basé sur le numéro
        if not conversation_id:
            conversation_id = f"whatsapp_{tenant_id}"

        logger.info(f"📝 WhatsApp message from {user_email} ({user_name}): {body[:100]}...")
        logger.info(f"🔧 Calling LLM service: {LLM_CHAT_ENDPOINT}")

        # Créer un JWT token pour l'utilisateur WhatsApp
        auth_token = create_whatsapp_user_token(user_info)
        if not auth_token:
            logger.error("❌ Failed to create auth token for WhatsApp user")
            return "Désolé, impossible de vous authentifier. Veuillez vérifier votre numéro WhatsApp dans votre profil."

        # Préparer la requête pour le service LLM (même format que frontend)
        payload = {
            "message": body,
            "tenant_id": tenant_id,
            "conversation_id": conversation_id,
            "use_json_search": True,
            "user_email": user_email,
        }

        # Headers avec authentification
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {auth_token}",  # JWT token pour authentification
            "Cache-Control": "no-cache",
        }

        logger.info(f"🔐 Authenticated request to LLM service for {user_email}")

        # Appel HTTP au service LLM avec streaming
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", LLM_CHAT_ENDPOINT, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    logger.error(f"❌ LLM service error: {response.status_code}")
                    return "Désolé, le service d'assistance n'est pas disponible actuellement. Veuillez réessayer plus tard."

                # Collecter la réponse depuis le stream SSE
                answer_chunks = []
                source = "unknown"
                confidence = 0.0

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    try:
                        # Parse SSE event
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str.strip() == "[DONE]":
                            break

                        import json
                        event = json.loads(data_str)
                        event_type = event.get("type")

                        if event_type == "start":
                            source = event.get("source", "unknown")
                            confidence = event.get("confidence", 0.0)
                            logger.info(f"📥 Stream started: source={source}, confidence={confidence}")

                        elif event_type == "chunk":
                            content = event.get("content", "")
                            answer_chunks.append(content)

                        elif event_type == "end":
                            logger.info(f"✅ Stream completed: {len(answer_chunks)} chunks")

                    except json.JSONDecodeError:
                        continue

        # Assembler la réponse complète
        full_answer = "".join(answer_chunks)

        if not full_answer:
            logger.error("❌ No answer received from LLM service")
            return "Désolé, je n'ai pas pu générer une réponse. Veuillez réessayer."

        logger.info(
            f"✅ LLM response received for {user_email} | "
            f"source={source}, confidence={confidence:.2f}, "
            f"length={len(full_answer)} chars"
        )

        # ============================================================
        # 💾 SAVE TO DATABASE - WhatsApp conversations
        # ============================================================
        try:
            user_id = user_info.get("user_id")
            if user_id:
                # Detect language from user message
                detected_language = detect_language(body)

                # Generate session_id from conversation_id (or create new UUID)
                # conversation_id format: "whatsapp_{phone_number}"
                # We need a UUID for session_id
                session_id = str(uuid4())

                # Check if conversation already exists by session_id
                # For WhatsApp, we use a persistent session per phone number
                # So we'll use the conversation_id as a lookup key
                existing_conv = conversation_service.get_conversation_by_session(conversation_id)

                if existing_conv:
                    # Add messages to existing conversation
                    conversation_service.add_message(
                        conversation_id=existing_conv["id"],
                        role="user",
                        content=body,
                        media_url=media_url,
                        media_type=media_type
                    )
                    conversation_service.add_message(
                        conversation_id=existing_conv["id"],
                        role="assistant",
                        content=full_answer,
                        response_source=source,
                        response_confidence=confidence
                    )
                    logger.info(f"💾 WhatsApp messages saved to existing conversation: {existing_conv['id']}")
                else:
                    # Create new conversation with first Q&A
                    result = conversation_service.create_conversation(
                        session_id=conversation_id,  # Use conversation_id as session_id for WhatsApp
                        user_id=user_id,
                        user_message=body,
                        assistant_response=full_answer,
                        language=detected_language,
                        response_source=source,
                        response_confidence=confidence,
                        user_media_url=media_url,
                        user_media_type=media_type
                    )
                    logger.info(f"💾 WhatsApp conversation created: {result['conversation_id']}")
            else:
                logger.warning("⚠️ Cannot save WhatsApp conversation: user_id not found in user_info")
        except Exception as e:
            # Don't block user response if DB save fails
            logger.error(f"❌ Failed to save WhatsApp conversation to database: {e}", exc_info=True)

        return full_answer

    except httpx.TimeoutException:
        logger.error("❌ LLM service timeout")
        return "Désolé, le traitement de votre question prend trop de temps. Veuillez réessayer."
    except httpx.RequestError as e:
        logger.error(f"❌ LLM service request error: {e}")
        return "Désolé, impossible de contacter le service d'assistance. Veuillez réessayer plus tard."
    except Exception as e:
        logger.error(f"❌ Error handling WhatsApp text message: {e}", exc_info=True)
        return "Désolé, une erreur s'est produite lors du traitement de votre message. Veuillez réessayer."


async def handle_audio_message(from_number: str, media_url: str, user_info: Dict[str, Any]) -> str:
    """
    Traite un message vocal WhatsApp avec transcription Whisper + RAG

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        media_url: URL du fichier audio (Twilio)
        user_info: Informations de l'utilisateur

    Returns:
        Réponse de l'assistant AI basée sur la transcription
    """
    try:
        user_email = user_info.get("user_email")
        logger.info(f"🎤 Audio message from {user_email}: {media_url}")

        # Créer un JWT token pour l'authentification
        auth_token = create_whatsapp_user_token(user_info)
        if not auth_token:
            logger.error("❌ Failed to create auth token for audio transcription")
            return "Désolé, impossible de vous authentifier pour la transcription audio."

        # Étape 1: Télécharger l'audio depuis Twilio
        logger.info(f"📥 Downloading audio from Twilio: {media_url}")

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Télécharger l'audio avec auth Twilio
            audio_response = await client.get(
                media_url,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            )

            if audio_response.status_code != 200:
                logger.error(f"❌ Failed to download audio: {audio_response.status_code}")
                return "Désolé, je n'ai pas pu télécharger votre message vocal."

            audio_data = audio_response.content
            content_type = audio_response.headers.get("Content-Type", "audio/ogg")

            logger.info(f"✅ Audio downloaded: {len(audio_data)} bytes, type: {content_type}")

        # Étape 1b: Upload audio vers DigitalOcean Spaces pour stockage permanent
        permanent_audio_url = media_url  # Fallback to Twilio URL
        try:
            user_id = user_info.get("user_id")
            if user_id:
                # Déterminer extension
                extension_map = {
                    "audio/ogg": "ogg",
                    "audio/mpeg": "mp3",
                    "audio/mp4": "m4a",
                    "audio/x-m4a": "m4a",
                    "audio/wav": "wav"
                }
                extension = extension_map.get(content_type, "ogg")

                # Générer clé et uploader
                spaces_key = audio_storage_service.generate_audio_key(user_id, "whatsapp", extension)
                permanent_audio_url = audio_storage_service.upload_audio(
                    audio_data=audio_data,
                    spaces_key=spaces_key,
                    content_type=content_type,
                    metadata={
                        "user_email": user_email,
                        "twilio_url": media_url,
                        "transcription_pending": "true"
                    }
                )
                logger.info(f"✅ Audio uploaded to Spaces: {permanent_audio_url}")
            else:
                logger.warning("⚠️ Cannot upload audio to Spaces: user_id not found")
        except Exception as e:
            # Don't block transcription if Spaces upload fails
            logger.error(f"❌ Failed to upload audio to Spaces (non-blocking): {e}")

        # Étape 2: Transcrire avec Whisper API
        logger.info(f"🔊 Transcribing audio with Whisper API...")

        # Déterminer l'extension du fichier audio
        # WhatsApp envoie généralement en OGG/Opus
        file_extension = "ogg"
        if "mp3" in content_type:
            file_extension = "mp3"
        elif "mp4" in content_type or "m4a" in content_type:
            file_extension = "m4a"
        elif "wav" in content_type:
            file_extension = "wav"

        # Appeler Whisper API via OpenAI
        import openai
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if not openai_api_key:
            logger.error("❌ OPENAI_API_KEY not configured")
            return "Désolé, le service de transcription n'est pas configuré."

        # Créer un fichier temporaire pour Whisper (nécessaire pour l'API)
        import io
        audio_file = io.BytesIO(audio_data)
        audio_file.name = f"whatsapp_audio.{file_extension}"

        # Transcrire avec Whisper
        client_openai = openai.OpenAI(api_key=openai_api_key)
        transcription = client_openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="fr",  # Forcer le français (peut être détecté automatiquement si omis)
        )

        transcribed_text = transcription.text.strip()

        if not transcribed_text:
            logger.error("❌ Whisper returned empty transcription")
            return "Désolé, je n'ai pas pu comprendre votre message vocal. Pouvez-vous réessayer ?"

        logger.info(f"✅ Transcription completed: '{transcribed_text[:100]}...'")

        # Étape 3: Traiter le texte transcrit avec RAG (comme un message texte normal)
        logger.info(f"🤖 Processing transcription with RAG...")

        # Réutiliser handle_text_message avec le texte transcrit
        # Pass permanent_audio_url (Spaces URL or Twilio fallback)
        response = await handle_text_message(
            from_number=from_number,
            body=transcribed_text,
            user_info=user_info,
            media_url=permanent_audio_url,  # Permanent Spaces URL (or Twilio fallback)
            media_type="audio"
        )

        # Préfixer la réponse pour indiquer que c'était un message vocal
        response_with_context = f"🎤 Message vocal transcrit: \"{transcribed_text}\"\n\n{response}"

        logger.info(f"✅ Audio message processed successfully for {user_email}")

        return response_with_context

    except openai.APIError as e:
        logger.error(f"❌ OpenAI Whisper API error: {e}")
        return "Désolé, une erreur s'est produite lors de la transcription. Veuillez réessayer."
    except httpx.TimeoutException:
        logger.error("❌ Audio download timeout")
        return "Désolé, le téléchargement de votre message vocal a pris trop de temps. Veuillez réessayer."
    except Exception as e:
        logger.error(f"❌ Error handling audio message: {e}", exc_info=True)
        return "Désolé, une erreur s'est produite lors du traitement de votre message vocal. Veuillez réessayer."


async def handle_image_message(from_number: str, media_url: str, user_info: Dict[str, Any], message_text: Optional[str] = None) -> str:
    """
    Traite une image WhatsApp avec analyse GPT-4 Vision

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        media_url: URL de l'image (Twilio)
        user_info: Informations de l'utilisateur
        message_text: Texte accompagnant l'image (optionnel)

    Returns:
        Analyse de l'image par GPT-4 Vision
    """
    try:
        user_email = user_info.get("user_email")
        logger.info(f"🖼️ Image message from {user_email}: {media_url}")

        # Vérifier le plan de l'utilisateur pour l'analyse d'images
        from app.services.usage_limiter import get_user_plan_and_quota
        plan_name, _, _ = get_user_plan_and_quota(user_email)
        plan_lower = plan_name.lower() if plan_name else "essential"

        # Analyse d'images réservée aux plans Pro, Elite et Intelia
        if plan_lower not in ["pro", "elite", "intelia"]:
            logger.warning(f"❌ Image analysis denied for {user_email} (plan: {plan_name})")
            return "🔒 L'analyse d'images est réservée aux plans Pro et Elite. Mettez à niveau votre abonnement sur https://intelia.expert pour accéder à cette fonctionnalité."

        # Créer un JWT token pour l'authentification
        auth_token = create_whatsapp_user_token(user_info)
        if not auth_token:
            logger.error("❌ Failed to create auth token for image analysis")
            return "Désolé, impossible de vous authentifier pour l'analyse d'image."

        # Étape 1: Télécharger l'image depuis Twilio
        logger.info(f"📥 Downloading image from Twilio: {media_url}")

        # Twilio nécessite l'authentification pour télécharger les médias
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Télécharger l'image avec auth Twilio
            image_response = await client.get(
                media_url,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            )

            if image_response.status_code != 200:
                logger.error(f"❌ Failed to download image: {image_response.status_code}")
                return "Désolé, je n'ai pas pu télécharger votre image."

            image_data = image_response.content
            content_type = image_response.headers.get("Content-Type", "image/jpeg")

            logger.info(f"✅ Image downloaded: {len(image_data)} bytes, type: {content_type}")

        # Étape 2: Préparer la requête pour le service LLM Vision
        tenant_id = from_number.replace("whatsapp:", "").strip()

        # Message par défaut si pas de texte
        if not message_text:
            message_text = "Qu'est-ce que vous voyez dans cette image liée à l'aviculture ?"

        # Créer FormData (équivalent HTTP de FormData JavaScript)
        from httpx import AsyncClient

        # Préparer les fichiers et données
        files = {
            'files': ('whatsapp_image.jpg', image_data, content_type)
        }

        data = {
            'message': message_text,
            'tenant_id': tenant_id,
            'language': 'fr',
            'use_rag_context': 'true'
        }

        headers = {
            "Authorization": f"Bearer {auth_token}",
        }

        # Étape 3: Appeler l'endpoint vision du LLM
        llm_vision_endpoint = f"{LLM_SERVICE_URL}/chat-with-image"
        logger.info(f"🔧 Calling LLM Vision service: {llm_vision_endpoint}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            vision_response = await client.post(
                llm_vision_endpoint,
                files=files,
                data=data,
                headers=headers
            )

            if vision_response.status_code != 200:
                logger.error(f"❌ LLM Vision error: {vision_response.status_code}")
                error_detail = vision_response.text[:200]
                logger.error(f"Error details: {error_detail}")
                return "Désolé, je n'ai pas pu analyser votre image. Veuillez réessayer."

            vision_data = vision_response.json()

            if not vision_data.get("success") or not vision_data.get("analysis"):
                logger.error("❌ Vision API returned unsuccessful response")
                return "Désolé, l'analyse de l'image a échoué. Veuillez réessayer."

            analysis = vision_data["analysis"]
            model = vision_data.get("metadata", {}).get("model", "unknown")

            logger.info(
                f"✅ Vision analysis received for {user_email} | "
                f"model={model}, length={len(analysis)} chars"
            )

            # ============================================================
            # 💾 SAVE TO DATABASE - WhatsApp image analysis
            # ============================================================
            try:
                user_id = user_info.get("user_id")
                if user_id:
                    # Detect language from message_text
                    detected_language = detect_language(message_text)

                    # Use same session logic as text messages
                    conversation_id = f"whatsapp_{tenant_id}"
                    existing_conv = conversation_service.get_conversation_by_session(conversation_id)

                    if existing_conv:
                        # Add messages to existing conversation
                        conversation_service.add_message(
                            conversation_id=existing_conv["id"],
                            role="user",
                            content=f"[IMAGE] {message_text}",  # Prefix to indicate image
                            media_url=media_url,  # Save Twilio image URL
                            media_type="image"
                        )
                        conversation_service.add_message(
                            conversation_id=existing_conv["id"],
                            role="assistant",
                            content=analysis,
                            response_source="vision",
                            response_confidence=None  # Vision API doesn't return confidence
                        )
                        logger.info(f"💾 WhatsApp image messages saved to existing conversation: {existing_conv['id']}")
                    else:
                        # Create new conversation with image Q&A
                        result = conversation_service.create_conversation(
                            session_id=conversation_id,
                            user_id=user_id,
                            user_message=f"[IMAGE] {message_text}",
                            assistant_response=analysis,
                            language=detected_language,
                            response_source="vision",
                            response_confidence=None,
                            user_media_url=media_url,  # Save Twilio image URL
                            user_media_type="image"
                        )
                        logger.info(f"💾 WhatsApp image conversation created: {result['conversation_id']}")
                else:
                    logger.warning("⚠️ Cannot save WhatsApp image conversation: user_id not found in user_info")
            except Exception as e:
                # Don't block user response if DB save fails
                logger.error(f"❌ Failed to save WhatsApp image conversation to database: {e}", exc_info=True)

            return analysis

    except httpx.TimeoutException:
        logger.error("❌ LLM Vision service timeout")
        return "Désolé, l'analyse de votre image prend trop de temps. Veuillez réessayer."
    except httpx.RequestError as e:
        logger.error(f"❌ LLM Vision request error: {e}")
        return "Désolé, impossible de contacter le service d'analyse d'images. Veuillez réessayer plus tard."
    except Exception as e:
        logger.error(f"❌ Error handling image message: {e}", exc_info=True)
        return "Désolé, une erreur s'est produite lors de l'analyse de votre image. Veuillez réessayer."


async def handle_unknown_user(from_number: str) -> str:
    """
    Gère un message d'un numéro WhatsApp non reconnu

    Args:
        from_number: Numéro WhatsApp inconnu

    Returns:
        Message d'aide pour l'utilisateur
    """
    clean_number = from_number.replace("whatsapp:", "").strip()
    logger.warning(f"⚠️ Unknown WhatsApp number: {clean_number}")

    return (
        "🔒 Numéro non reconnu.\n\n"
        "Pour utiliser Intelia Cognito via WhatsApp:\n"
        "1. Connectez-vous sur https://expert.intelia.com\n"
        "2. Ajoutez votre numéro WhatsApp dans votre profil\n"
        "3. Vérifiez le code reçu\n\n"
        "Ensuite, vous pourrez utiliser l'assistant IA via WhatsApp!"
    )


def send_whatsapp_message(to_number: str, body: str, media_url: str = None) -> bool:
    """
    Envoie un message WhatsApp via Twilio
    Tronque automatiquement les longs messages à 1600 caractères (limite Twilio)

    Args:
        to_number: Numéro destinataire (format: whatsapp:+1234567890)
        body: Contenu du message
        media_url: URL d'un média (optionnel)

    Returns:
        True si envoyé avec succès, False sinon
    """
    try:
        if not twilio_client:
            logger.error("❌ Twilio client not initialized")
            return False

        # Limite Twilio-WhatsApp: 1600 caractères
        # Note: Emojis comptent plusieurs caractères, donc on utilise une marge de sécurité
        MAX_LENGTH = 1300  # Marge pour les emojis/caractères spéciaux

        # Supprimer les emojis (Meta peut les bloquer)
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        body = emoji_pattern.sub('', body)

        # Tronquer le message si nécessaire
        if len(body) > MAX_LENGTH:
            logger.warning(f"⚠️ Message trop long ({len(body)} chars), troncature à {MAX_LENGTH} chars")
            body = body[:MAX_LENGTH - 3] + "..."  # -3 pour les "..."

        message_params = {
            "from_": TWILIO_WHATSAPP_NUMBER,
            "to": to_number,
            "body": body
        }

        if media_url:
            message_params["media_url"] = [media_url]

        message = twilio_client.messages.create(**message_params)
        logger.info(f"✅ WhatsApp message sent: {message.sid}")
        return True

    except Exception as e:
        logger.error(f"❌ Error sending WhatsApp message: {e}")
        return False


# ==================== WEBHOOK ENDPOINT ====================

@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(None),
    MessageSid: str = Form(...),
    NumMedia: int = Form(0),
    MediaUrl0: str = Form(None),
    MediaContentType0: str = Form(None)
):
    """
    Endpoint principal pour recevoir les webhooks WhatsApp de Twilio

    Événements supportés:
    - Messages texte
    - Messages vocaux (audio)
    - Images
    - Autres médias
    """
    logger.info(f"📥 WhatsApp webhook received from {From}")

    # Valider la signature Twilio (sécurité)
    if request_validator:
        try:
            # Récupérer la signature
            signature = request.headers.get("X-Twilio-Signature", "")

            # Construire l'URL publique que Twilio a appelée
            # Twilio signe avec l'URL publique, pas l'URL interne du container
            public_url = "https://expert.intelia.com/api/v1/whatsapp/webhook"

            # Récupérer tous les paramètres du formulaire
            form_data = await request.form()
            params = dict(form_data)

            # Valider la signature
            if not request_validator.validate(public_url, params, signature):
                logger.error(f"❌ Invalid Twilio signature for URL: {public_url}")
                raise HTTPException(status_code=403, detail="Invalid signature")

            logger.info("✅ Twilio signature verified")
        except HTTPException:
            raise  # Re-raise validation failures
        except Exception as e:
            logger.error(f"❌ Signature validation error: {e}", exc_info=True)
            # En développement, on peut continuer sans validation
            logger.warning("⚠️ Continuing without signature validation (dev mode)")

    # Identifier l'utilisateur
    user_info = get_user_by_whatsapp_number(From)

    if not user_info:
        # Numéro non reconnu
        response_text = await handle_unknown_user(From)
        send_whatsapp_message(From, response_text)

        return {"status": "unknown_user", "message": "User not recognized"}

    # Déterminer le type de message et envoyer l'accusé de réception immédiat
    response_text = None
    message_type = "text"

    try:
        # 🎯 ENVOI IMMÉDIAT DE L'ACCUSÉ DE RÉCEPTION
        # Avant de commencer le traitement (qui peut prendre du temps),
        # on envoie un message immédiat pour informer l'utilisateur
        if NumMedia > 0 and MediaUrl0:
            # Message avec média
            if MediaContentType0 and MediaContentType0.startswith("audio/"):
                message_type = "audio"
                # Envoyer immédiatement l'accusé de réception pour audio
                ack_message = get_acknowledgment_message("audio", Body or "")
                send_whatsapp_message(From, ack_message)
                logger.info(f"📤 Acknowledgment sent (audio): {ack_message}")

                response_text = await handle_audio_message(From, MediaUrl0, user_info)
            elif MediaContentType0 and MediaContentType0.startswith("image/"):
                message_type = "image"
                # Envoyer immédiatement l'accusé de réception pour image
                ack_message = get_acknowledgment_message("image", Body or "")
                send_whatsapp_message(From, ack_message)
                logger.info(f"📤 Acknowledgment sent (image): {ack_message}")

                # Passer le texte du message s'il y en a un avec l'image
                response_text = await handle_image_message(From, MediaUrl0, user_info, Body)
            else:
                message_type = "media"
                response_text = "Type de fichier non supporté pour le moment."
        elif Body:
            # Message texte
            message_type = "text"
            # Envoyer immédiatement l'accusé de réception pour texte
            ack_message = get_acknowledgment_message("text", Body)
            send_whatsapp_message(From, ack_message)
            logger.info(f"📤 Acknowledgment sent (text): {ack_message}")

            response_text = await handle_text_message(From, Body, user_info)
        else:
            response_text = "Message vide reçu."

        # Envoyer la réponse
        if response_text:
            # Attendre 10 secondes après l'accusé de réception (limite Meta: 1 msg/6s par utilisateur)
            # On attend 10s pour être sûr de respecter la limite
            time.sleep(10)
            send_whatsapp_message(From, response_text)

        logger.info(f"✅ WhatsApp message processed: {MessageSid}")

        return {"status": "success", "message_type": message_type}

    except Exception as e:
        logger.error(f"❌ Error processing WhatsApp message: {e}", exc_info=True)

        # Envoyer message d'erreur à l'utilisateur
        send_whatsapp_message(
            From,
            "Désolé, une erreur s'est produite lors du traitement de votre message. "
            "Veuillez réessayer dans quelques instants."
        )

        return {"status": "error", "message": str(e)}


@router.get("/webhook/test")
async def test_whatsapp_webhook():
    """
    Endpoint de test pour vérifier que le webhook WhatsApp est accessible
    """
    return {
        "status": "ok",
        "message": "WhatsApp webhook endpoint is ready",
        "twilio_configured": twilio_client is not None,
        "whatsapp_number": TWILIO_WHATSAPP_NUMBER,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status")
async def whatsapp_status():
    """
    Retourne le statut de la configuration WhatsApp
    """
    # Test LLM service connectivity
    llm_service_available = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LLM_SERVICE_URL}/health")
            llm_service_available = response.status_code == 200
    except Exception as e:
        logger.warning(f"⚠️ LLM service health check failed: {e}")

    return {
        "whatsapp_enabled": twilio_client is not None,
        "twilio_account_sid": TWILIO_ACCOUNT_SID[:8] + "..." if TWILIO_ACCOUNT_SID else None,
        "whatsapp_number": TWILIO_WHATSAPP_NUMBER,
        "signature_validation": request_validator is not None,
        "llm_integration": {
            "architecture": "microservices_http",
            "llm_service_url": LLM_SERVICE_URL,
            "llm_service_available": llm_service_available,
            "endpoint": LLM_CHAT_ENDPOINT,
            "version": "2.1_microservices",
        }
    }

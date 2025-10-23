# app/api/v1/whatsapp_webhooks.py
# -*- coding: utf-8 -*-
"""
WhatsApp Webhook Handler via Twilio
Traite les messages WhatsApp entrants et envoie les réponses
Version: 2.2 - HTTP integration with LLM service + authentication
"""

import os
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

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
            "email, whatsapp_number, first_name, last_name, plan, user_type"
        ).eq("whatsapp_number", clean_number).execute()

        if response.data and len(response.data) > 0:
            user = response.data[0]
            logger.info(f"✅ User found for WhatsApp: {user.get('email')}")
            return {
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

async def handle_text_message(from_number: str, body: str, user_info: Dict[str, Any], conversation_id: Optional[str] = None) -> str:
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
    Traite un message vocal WhatsApp

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        media_url: URL du fichier audio
        user_info: Informations de l'utilisateur

    Returns:
        Réponse à envoyer
    """
    try:
        user_email = user_info.get("user_email")
        logger.info(f"🎤 Audio message from {user_email}: {media_url}")

        # TODO: Intégrer avec votre système de transcription existant
        # Pour l'instant, réponse simple
        response = "Message vocal reçu. Transcription et traitement en cours..."

        return response
    except Exception as e:
        logger.error(f"❌ Error handling audio message: {e}")
        return "Désolé, je n'ai pas pu traiter votre message vocal."


async def handle_image_message(from_number: str, media_url: str, user_info: Dict[str, Any]) -> str:
    """
    Traite une image WhatsApp

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        media_url: URL de l'image
        user_info: Informations de l'utilisateur

    Returns:
        Réponse à envoyer
    """
    try:
        user_email = user_info.get("user_email")
        logger.info(f"🖼️ Image message from {user_email}: {media_url}")

        # TODO: Intégrer avec votre système de vision multimodale
        # Pour l'instant, réponse simple
        response = "Image reçue. Analyse en cours avec notre système de vision..."

        return response
    except Exception as e:
        logger.error(f"❌ Error handling image message: {e}")
        return "Désolé, je n'ai pas pu analyser votre image."


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
            # Récupérer l'URL complète et la signature
            url = str(request.url)
            signature = request.headers.get("X-Twilio-Signature", "")

            # Récupérer tous les paramètres du formulaire
            form_data = await request.form()
            params = dict(form_data)

            # Valider la signature
            if not request_validator.validate(url, params, signature):
                logger.error("❌ Invalid Twilio signature")
                raise HTTPException(status_code=403, detail="Invalid signature")

            logger.info("✅ Twilio signature verified")
        except Exception as e:
            logger.error(f"❌ Signature validation error: {e}")
            # En développement, on peut continuer sans validation
            logger.warning("⚠️ Continuing without signature validation (dev mode)")

    # Identifier l'utilisateur
    user_info = get_user_by_whatsapp_number(From)

    if not user_info:
        # Numéro non reconnu
        response_text = await handle_unknown_user(From)
        send_whatsapp_message(From, response_text)

        return {"status": "unknown_user", "message": "User not recognized"}

    # Déterminer le type de message
    response_text = None
    message_type = "text"

    try:
        if NumMedia > 0 and MediaUrl0:
            # Message avec média
            if MediaContentType0 and MediaContentType0.startswith("audio/"):
                message_type = "audio"
                response_text = await handle_audio_message(From, MediaUrl0, user_info)
            elif MediaContentType0 and MediaContentType0.startswith("image/"):
                message_type = "image"
                response_text = await handle_image_message(From, MediaUrl0, user_info)
            else:
                message_type = "media"
                response_text = "Type de fichier non supporté pour le moment."
        elif Body:
            # Message texte
            message_type = "text"
            response_text = await handle_text_message(From, Body, user_info)
        else:
            response_text = "Message vide reçu."

        # Envoyer la réponse
        if response_text:
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

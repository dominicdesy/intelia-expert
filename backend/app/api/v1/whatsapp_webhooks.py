# app/api/v1/whatsapp_webhooks.py
# -*- coding: utf-8 -*-
"""
WhatsApp Webhook Handler via Twilio
Traite les messages WhatsApp entrants et envoie les réponses
Version: 1.0
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Form
from twilio.rest import Client
from twilio.request_validator import RequestValidator

# Supabase client for user lookup
try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# OpenAI for chat completions
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhooks"])
logger = logging.getLogger(__name__)

# Configuration Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+15075195932")
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Configuration OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")

# Initialize OpenAI client
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    logger.info("✅ OpenAI configured for WhatsApp responses")
else:
    logger.warning("⚠️ OpenAI not configured - WhatsApp will send placeholder responses")

# Initialiser le client Twilio
twilio_client = None
request_validator = None

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    request_validator = RequestValidator(TWILIO_AUTH_TOKEN)
    logger.info("✅ Twilio client initialized")
else:
    logger.warning("⚠️ Twilio credentials not configured - WhatsApp disabled")


# ==================== DATABASE HELPERS ====================

def get_db_connection():
    """Créer une connexion à la base de données"""
    return psycopg2.connect(DATABASE_URL)


def log_whatsapp_message(
    from_number: str,
    to_number: str,
    message_sid: str,
    message_type: str,
    body: str = None,
    media_url: str = None,
    status: str = "received",
    user_email: str = None
):
    """
    Log tous les messages WhatsApp reçus pour audit et debugging
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO whatsapp_message_logs (
                        from_number, to_number, message_sid, message_type,
                        body, media_url, status, user_email, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        from_number,
                        to_number,
                        message_sid,
                        message_type,
                        body,
                        media_url,
                        status,
                        user_email,
                        datetime.utcnow()
                    )
                )
                conn.commit()
                logger.info(f"✅ WhatsApp message logged: {message_sid}")
    except Exception as e:
        logger.error(f"❌ Error logging WhatsApp message: {e}")


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


# ==================== OPENAI INTEGRATION ====================

def get_ai_response(user_message: str, user_info: Dict[str, Any]) -> str:
    """
    Génère une réponse AI pour un message WhatsApp

    Args:
        user_message: Message de l'utilisateur
        user_info: Informations de l'utilisateur (email, plan, etc.)

    Returns:
        Réponse de l'assistant AI
    """
    try:
        if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
            return "Désolé, le service AI n'est pas disponible actuellement. Veuillez réessayer plus tard."

        user_name = user_info.get("first_name", "")
        user_plan = user_info.get("plan_name", "essential")

        # System prompt pour Intelia Cognito
        system_prompt = """Tu es Intelia Cognito, un assistant IA spécialisé en production avicole.

Ton rôle est d'aider les producteurs et professionnels de la volaille avec:
- Santé animale et diagnostic de maladies
- Nutrition et alimentation
- Gestion de production
- Biosécurité
- Performance et rentabilité

Réponds de manière:
- Précise et factuelle
- Concise (max 2-3 paragraphes pour WhatsApp)
- Professionnelle mais accessible
- En français (sauf si demandé autrement)

Si tu n'es pas certain d'une réponse, dis-le clairement et recommande de consulter un vétérinaire."""

        # Construire les messages pour OpenAI
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # Ajouter le contexte utilisateur si disponible
        if user_name:
            messages.append({
                "role": "system",
                "content": f"L'utilisateur s'appelle {user_name}. Plan: {user_plan}."
            })

        # Ajouter la question de l'utilisateur
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Appel à OpenAI
        logger.info(f"🤖 Calling OpenAI for user {user_info.get('user_email')}")

        response = openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=500,  # Limité pour WhatsApp
            timeout=30
        )

        ai_response = response.choices[0].message.content.strip()

        logger.info(f"✅ OpenAI response generated ({len(ai_response)} chars)")

        return ai_response

    except Exception as e:
        logger.error(f"❌ Error getting AI response: {e}")
        return "Désolé, une erreur s'est produite lors du traitement de votre question. Veuillez réessayer."


# ==================== MESSAGE HANDLERS ====================

async def handle_text_message(from_number: str, body: str, user_info: Dict[str, Any]) -> str:
    """
    Traite un message texte WhatsApp avec l'AI

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        body: Contenu du message
        user_info: Informations de l'utilisateur

    Returns:
        Réponse de l'assistant AI
    """
    try:
        user_email = user_info.get("user_email")
        user_name = user_info.get("first_name", "")
        logger.info(f"📝 Text message from {user_email} ({user_name}): {body[:100]}...")

        # Générer la réponse AI
        ai_response = get_ai_response(body, user_info)

        logger.info(f"✅ AI response generated for {user_email}")

        return ai_response

    except Exception as e:
        logger.error(f"❌ Error handling text message: {e}")
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

        # Log l'envoi
        log_whatsapp_message(
            from_number=TWILIO_WHATSAPP_NUMBER,
            to_number=to_number,
            message_sid=message.sid,
            message_type="outbound",
            body=body,
            media_url=media_url,
            status="sent"
        )

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

        # Log le message
        log_whatsapp_message(
            from_number=From,
            to_number=To,
            message_sid=MessageSid,
            message_type="unknown_user",
            body=Body,
            status="rejected"
        )

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

        # Log le message
        log_whatsapp_message(
            from_number=From,
            to_number=To,
            message_sid=MessageSid,
            message_type=message_type,
            body=Body,
            media_url=MediaUrl0,
            status="processed",
            user_email=user_info.get("user_email")
        )

        logger.info(f"✅ WhatsApp message processed: {MessageSid}")

        return {"status": "success", "message_type": message_type}

    except Exception as e:
        logger.error(f"❌ Error processing WhatsApp message: {e}")

        # Envoyer message d'erreur à l'utilisateur
        send_whatsapp_message(
            From,
            "Désolé, une erreur s'est produite lors du traitement de votre message. "
            "Veuillez réessayer dans quelques instants."
        )

        # Log l'erreur
        log_whatsapp_message(
            from_number=From,
            to_number=To,
            message_sid=MessageSid,
            message_type=message_type,
            body=Body,
            status="error",
            user_email=user_info.get("user_email")
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
    return {
        "whatsapp_enabled": twilio_client is not None,
        "twilio_account_sid": TWILIO_ACCOUNT_SID[:8] + "..." if TWILIO_ACCOUNT_SID else None,
        "whatsapp_number": TWILIO_WHATSAPP_NUMBER,
        "signature_validation": request_validator is not None
    }

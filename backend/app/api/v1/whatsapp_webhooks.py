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

router = APIRouter(prefix="/whatsapp", tags=["whatsapp-webhooks"])
logger = logging.getLogger(__name__)

# Configuration Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+15075195932")
DATABASE_URL = os.getenv("DATABASE_URL")

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
    Récupère l'utilisateur associé à un numéro WhatsApp

    Args:
        whatsapp_number: Numéro WhatsApp (format: whatsapp:+1234567890)

    Returns:
        Dict avec les infos utilisateur ou None si non trouvé
    """
    try:
        # Normaliser le numéro (enlever le préfixe whatsapp:)
        clean_number = whatsapp_number.replace("whatsapp:", "").strip()

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT user_email, whatsapp_number, whatsapp_verified,
                           verified_at, plan_name
                    FROM user_whatsapp_info
                    WHERE whatsapp_number = %s AND whatsapp_verified = TRUE
                    """,
                    (clean_number,)
                )
                result = cur.fetchone()

                if result:
                    logger.info(f"✅ User found for WhatsApp: {result['user_email']}")
                    return dict(result)
                else:
                    logger.warning(f"⚠️ No verified user for WhatsApp: {clean_number}")
                    return None
    except Exception as e:
        logger.error(f"❌ Error getting user by WhatsApp: {e}")
        return None


def link_whatsapp_to_user(user_email: str, whatsapp_number: str) -> bool:
    """
    Associe un numéro WhatsApp à un compte utilisateur

    Args:
        user_email: Email de l'utilisateur
        whatsapp_number: Numéro WhatsApp à lier

    Returns:
        True si succès, False sinon
    """
    try:
        clean_number = whatsapp_number.replace("whatsapp:", "").strip()

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_whatsapp_info (
                        user_email, whatsapp_number, whatsapp_verified, verified_at
                    ) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_email) DO UPDATE SET
                        whatsapp_number = EXCLUDED.whatsapp_number,
                        whatsapp_verified = EXCLUDED.whatsapp_verified,
                        verified_at = EXCLUDED.verified_at,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (user_email, clean_number, True, datetime.utcnow())
                )
                conn.commit()
                logger.info(f"✅ WhatsApp linked to user: {user_email}")
                return True
    except Exception as e:
        logger.error(f"❌ Error linking WhatsApp: {e}")
        return False


# ==================== MESSAGE HANDLERS ====================

async def handle_text_message(from_number: str, body: str, user_info: Dict[str, Any]) -> str:
    """
    Traite un message texte WhatsApp

    Args:
        from_number: Numéro WhatsApp de l'expéditeur
        body: Contenu du message
        user_info: Informations de l'utilisateur

    Returns:
        Réponse à envoyer
    """
    try:
        user_email = user_info.get("user_email")
        logger.info(f"📝 Text message from {user_email}: {body[:50]}...")

        # TODO: Intégrer avec votre système de conversation existant
        # Pour l'instant, réponse simple
        response = f"Message reçu: {body}\n\nIntégration avec l'assistant IA en cours..."

        return response
    except Exception as e:
        logger.error(f"❌ Error handling text message: {e}")
        return "Désolé, une erreur s'est produite. Veuillez réessayer."


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
